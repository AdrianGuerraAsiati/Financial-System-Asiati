/**
 * ASIATI · aviso de cambio de Google Sheets.
 *
 * Configurar en Apps Script > Project Settings > Script Properties:
 *   ASIATI_WEBHOOK_URL
 *   ASIATI_WEBHOOK_SECRET
 *   ASIATI_MODULE          cartera | compras
 *   ASIATI_EMPRESA_ID      id numérico de la empresa
 *
 * Ejecutar asiatiInstallTriggers() una sola vez con permisos del propietario.
 * Los triggers solo notifican: el backend aplica debounce y decide cuándo leer.
 */

function asiatiNotifySheetChange(e) {
  const props = PropertiesService.getScriptProperties();
  const url = props.getProperty("ASIATI_WEBHOOK_URL");
  const secret = props.getProperty("ASIATI_WEBHOOK_SECRET");
  const modulo = props.getProperty("ASIATI_MODULE");
  const empresaId = Number(props.getProperty("ASIATI_EMPRESA_ID"));

  if (!url || !secret || !modulo || !empresaId) {
    throw new Error("Faltan Script Properties de ASIATI.");
  }

  const spreadsheet = e && e.source
    ? e.source
    : SpreadsheetApp.getActiveSpreadsheet();
  const range = e && e.range ? e.range : null;

  const payload = {
    modulo: modulo,
    empresa_id: empresaId,
    spreadsheet_id: spreadsheet.getId(),
    hoja: range ? range.getSheet().getName() : null,
    rango: range ? range.getA1Notation() : null,
    tipo_evento: e && e.changeType ? e.changeType : "EDIT",
  };

  const response = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-ASIATI-Sheet-Secret": secret,
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });

  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    throw new Error(
      "ASIATI webhook respondió " + status + ": " + response.getContentText()
    );
  }
}

function asiatiInstallTriggers() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  ScriptApp.getProjectTriggers()
    .filter((trigger) => trigger.getHandlerFunction() === "asiatiNotifySheetChange")
    .forEach((trigger) => ScriptApp.deleteTrigger(trigger));

  ScriptApp.newTrigger("asiatiNotifySheetChange")
    .forSpreadsheet(spreadsheet)
    .onEdit()
    .create();

  ScriptApp.newTrigger("asiatiNotifySheetChange")
    .forSpreadsheet(spreadsheet)
    .onChange()
    .create();
}
