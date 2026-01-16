// ============================================
// CONFIGURAÇÃO DAS ABAS E COLUNAS
// ============================================
const ABA_ESPECIFICA = "Físicas/Eletrônicas";
const ABA_GERAL = "Geral";

// Mapeamento das Colunas (Baseado na sua imagem)
// A=0, B=1, C=2, D=3, E=4, F=5
const COLUNA_PROCESSO_INDEX = 3; // Coluna D

function doGet(e) {
  return handleRequest(e, 'GET');
}

function doPost(e) {
  return handleRequest(e, 'POST');
}

function handleRequest(e, type) {
  const lock = LockService.getScriptLock();
  lock.tryLock(10000); // Espera até 10s para evitar conflito

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    // --- LÓGICA DE CONSULTA (GET) ---
    // Usada para verificar se processo já existe (Apenas para Físicas/Eletrônicas)
    if (type === 'GET') {
      const processoBuscado = e.parameter.processo;
      
      // Se não tem processo (ex: Certidão Geral), não busca nada
      if (!processoBuscado) {
        return responseJSON({ status: 'success', encontrado: false });
      }

      const sheet = ss.getSheetByName(ABA_ESPECIFICA);
      if (!sheet) return responseJSON({ status: 'error', message: 'Aba específica não encontrada.' });

      const procLimpo = processoBuscado.replace(/[^0-9]/g, "");
      const data = sheet.getDataRange().getValues();
      
      let encontrado = false;
      let detalhes = {};

      // Começa da linha 1 (pula cabeçalho)
      for (let i = 1; i < data.length; i++) {
        const row = data[i];
        const procNaPlanilha = String(row[COLUNA_PROCESSO_INDEX]).replace(/[^0-9]/g, "");

        if (procNaPlanilha && procLimpo && procNaPlanilha.includes(procLimpo)) {
          encontrado = true;
          detalhes = {
            data_registro: formatarData(row[0]),
            consultor: row[1],
            chamado: row[2],
            processo: row[3],
            motivo: row[4],
            tipo: row[5]
          };
          break; 
        }
      }

      return responseJSON({
        status: 'success',
        encontrado: encontrado,
        dados: detalhes
      });
    }

    // --- LÓGICA DE GRAVAÇÃO (POST) ---
    if (type === 'POST') {
      const dataRec = JSON.parse(e.postData.contents);
      const tipo = dataRec.tipo_certidao; 
      
      // Define a aba de destino
      let nomeAbaDestino = ABA_ESPECIFICA; // Padrão
      if (tipo === "Geral") {
        nomeAbaDestino = ABA_GERAL;
      }

      const sheet = ss.getSheetByName(nomeAbaDestino);
      if (!sheet) return responseJSON({ status: 'error', message: `Aba '${nomeAbaDestino}' não encontrada.` });

      // Prepara a linha: A=Data, B=Consultor, C=Chamado, D=Processo, E=Motivo, F=Tipo
      const novaLinha = [
        new Date(),                      // A: Data Atual do Registro
        dataRec.consultor,               // B: Consultor
        dataRec.chamado || "-",          // C: Chamado (Traço se vazio/Geral)
        dataRec.processo || "-",         // D: Processo (Traço se vazio/Geral)
        dataRec.motivo,                  // E: Motivo
        dataRec.tipo_certidao            // F: Tipo da Declaração
      ];

      sheet.appendRow(novaLinha);
      
      return responseJSON({ status: 'success', message: `Salvo na aba ${nomeAbaDestino}` });
    }

  } catch (error) {
    return responseJSON({ status: 'error', message: error.toString() });
  } finally {
    lock.releaseLock();
  }
}

function responseJSON(content) {
  return ContentService
    .createTextOutput(JSON.stringify(content))
    .setMimeType(ContentService.MimeType.JSON);
}

function formatarData(dateObj) {
  if (!dateObj) return "";
  try {
    return Utilities.formatDate(new Date(dateObj), "GMT-3", "dd/MM/yyyy HH:mm");
  } catch (e) { return dateObj; }
}
