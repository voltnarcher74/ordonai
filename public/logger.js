/**
 * OrdonAI — Online Eval Logger
 * Logs user events to Google Sheets for production quality monitoring.
 * Events: extraction_completed, card_verified, modifier_used,
 *         schedule_confirmed, ics_downloaded
 */

const SESSION_ID = Math.random().toString(36).slice(2, 10);
const SHEET_URL  = 'https://script.google.com/macros/s/AKfycbxIigBTIa7b2EcDtXyWxGUnZH0uk93VH0ckzSvynVSSchx_v_1DHpRdH9spk89DLm8IvA/exec';

function logEvent(event, extra = {}) {
  const payload = {
    timestamp:    new Date().toISOString(),
    session_id:   SESSION_ID,
    event,
    med_name:     extra.med_name     || '',
    field:        extra.field        || '',
    value_before: extra.value_before || '',
    value_after:  extra.value_after  || '',
    meds_count:   extra.meds_count   || '',
    step:         extra.step         || '',
  };
  fetch(SHEET_URL, {
    method: 'POST',
    body:   JSON.stringify(payload),
  }).catch(() => {});
}
