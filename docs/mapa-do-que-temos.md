# Mapa do que temos / Map of what we have

Tabela de consulta ("preciso de → uso → manual"). O objetivo é que ninguém reinvente o que já existe.
Lookup table ("I need → use → manual"). The goal is that nobody reinvents what already exists.

## Ferramentas / Tools
| Preciso de... / I need... | Uso (local, grátis) / Use (local, free) | Onde entra / Where it fits |
|---|---|---|
| Transcrever, tempo por palavra / Transcribe, per-word timing | faster-whisper (GPU), WhisperX | `cacador/03_alinhar_whisperx.py`, `montagem/legenda_blocos.py` |
| Achar momentos / Find moments | funil / funnel: OpenCV + áudio + WhisperX + Florence-2 | `cacador/01…05` |
| Rosto para zoom / Face tracking for zoom | OpenCV + YuNet | `cacador/01_opencv_marcar.py` (tamanho do rosto / face size) |
| Estudar uma referência / Study a reference | análise quadro a quadro, quadros-chave / frame-by-frame, key frames | `estilo/analisa_ref.py`, `estilo/quadros_chave.py` |
| Comparar criadores / Compare creators | tabela de métricas / metrics table | `estilo/comparar_criadores.py` |
| Baixar referência escolhida por você / Download a reference you chose | yt-dlp | `estilo/baixar_refs.py` |
| Descrever quadros, ler texto na tela / Describe frames, read on-screen text | Florence-2 (GPU) | `cacador/florence_quadros.py` |
| Montar no editor / Assemble in the editor | DaVinci Resolve scripting / MCP bridge | `montagem/` (preparação e conferência / preparation and checks) |
| Converter, cortar, medir / Convert, cut, measure | ffmpeg / ffprobe | usado por vários scripts / used by several scripts |

## Scripts vivos / Live scripts (16 in the original working folder)
Este repositório publica a parte genérica deles / this repo publishes the generic part:

| Grupo / Group | Script |
|---|---|
| Caçador / Hunter | `01_opencv_marcar`, `02_audio_eventos`, `03_alinhar_whisperx`, `04_candidatos`, `05_tabela`, `florence_quadros` |
| Montagem / Assembly | `preparar_video`, `conferir_timeline`, `legenda_blocos` |
| Estilo / Style | `analisa_ref`, `quadros_chave`, `baixar_refs`, `comparar_criadores` (novo / new) |
| Guias e feedback / Guides and feedback | `mapa_dos_guias`, `feedback_pendente` |

## Regras de uso / Usage rules
- Script **só marca**; quem escolhe é a IA lendo a fala e o humano aprova. *Scripts only mark.*
- Um script só vira "oficial" depois de testado num caso real. *A script is official only after a real test.*
- Saída curta no terminal (≤ 20 linhas), o resto em arquivo. *Short terminal output, the rest in files.*
- Rodar de novo só repete o que falhou; nada é sobrescrito. *Re-running only repeats failures; nothing is overwritten.*
