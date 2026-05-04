/**
 * OrdonAI — Guardrails
 * Safety checks on Claude's output before showing results to user.
 * Called from analyzeFile() after parsing Claude's response.
 *
 * Returns: { blocked, blockReason, warnings }
 */

function runGuardrails(parsed) {
  const result = {
    blocked:     false,
    blockReason: '',
    warnings:    [],
  };

  const docType = parsed.document_type || 'prescription';
  const meds    = parsed.medications   || [];

  // ── Hard blocks ────────────────────────────────────────────────

  // Document is not a prescription
  if (docType === 'not_a_prescription') {
    result.blocked     = true;
    result.blockCode   = 'pas_ordonnance';
    result.blockReason = "Ce document ne semble pas être une ordonnance. Réessayez ou contactez-nous : aide@ordonai.fr";
    return result;
  }

  // Document is unreadable
  if (docType === 'unreadable') {
    result.blocked     = true;
    result.blockCode   = 'image_floue';
    result.blockReason = "L'image est floue, merci de soumettre une photo de meilleure qualité.";
    return result;
  }

  // No medications found on a valid prescription
  if (meds.length === 0) {
    result.blocked     = true;
    result.blockCode   = 'aucun_medicament';
    result.blockReason = "Aucun médicament détecté. Vérifiez que l'ordonnance est bien visible.";
    return result;
  }

  // Missing drug name
  const missingName = meds.find(m => !m.name || m.name.trim() === '');
  if (missingName) {
    result.blocked     = true;
    result.blockCode   = 'nom_manquant';
    result.blockReason = "Un médicament sans nom a été détecté — impossible de continuer. Vérifiez votre ordonnance.";
    return result;
  }

  // Duplicate medication (same name + dosage)
  const seen = {};
  for (const med of meds) {
    const key = `${med.name.trim().toLowerCase()}|${(med.dosage || '').trim().toLowerCase()}`;
    if (seen[key]) {
      result.blocked     = true;
      result.blockCode   = 'medicament_double';
      result.blockReason = `Le médicament "${med.name}${med.dosage ? ' ' + med.dosage : ''}" apparaît en double — veuillez vérifier votre ordonnance.`;
      return result;
    }
    seen[key] = true;
  }

  // ── Soft warnings ──────────────────────────────────────────────

  // Too many medications
  if (meds.length > 8) {
    result.warnings.push(`${meds.length} médicaments détectés — vérifiez attentivement.`);
  }

  // Per medication checks
  meds.forEach(med => {
    const label = med.name || 'Médicament inconnu';

    // Missing schedule
    if (!med.schedule || med.schedule.length === 0) {
      result.warnings.push(`Horaire manquant pour ${label} — vérifiez la fréquence.`);
    }

    // Unrealistic duration
    if (med.duration_days > 365) {
      result.warnings.push(`Durée inhabituelle pour ${label} (${med.duration_days} jours) — vérifiez.`);
    }
  });

  return result;
}
