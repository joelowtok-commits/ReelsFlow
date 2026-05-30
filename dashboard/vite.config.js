import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { exec, spawn } from 'child_process'
import fs from 'fs'
import path from 'path'
import os from 'os'
import http from 'http'
import https from 'https'
import Busboy from 'busboy'

// Load .env manually from parent directory or current directory
const parentEnv = path.join(process.cwd(), '..', '.env')
const localEnv = path.join(process.cwd(), '.env')
const envPath = fs.existsSync(parentEnv) ? parentEnv : (fs.existsSync(localEnv) ? localEnv : null)
if (envPath) {
  const envContent = fs.readFileSync(envPath, 'utf8')
  envContent.split(/\r?\n/).forEach(line => {
    const trimmed = line.trim()
    if (trimmed && !trimmed.startsWith('#')) {
      const eqIdx = trimmed.indexOf('=')
      if (eqIdx !== -1) {
        const key = trimmed.slice(0, eqIdx).trim()
        const value = trimmed.slice(eqIdx + 1).trim()
        const strippedValue = (value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))
          ? value.slice(1, -1)
          : value
        if (key && !process.env[key]) {
          process.env[key] = strippedValue
        }
      }
    }
  })
}

// Backend URL: defaults to localhost for local dev.
// Set VITE_BACKEND_URL=http://100.x.x.x:8000 to point to Kaggle/Colab GPU.
const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://localhost:8000'
const RENDER_URL = process.env.VITE_RENDER_URL || 'http://localhost:3100'

const googleDrivePath = process.env.GOOGLE_DRIVE_PATH;
if (googleDrivePath) {
  console.log(`📂 [Vite Config] Ruta de Google Drive detectada: ${googleDrivePath}`);
  try {
    fs.mkdirSync(path.join(googleDrivePath, 'uploads'), { recursive: true });
    fs.mkdirSync(path.join(googleDrivePath, 'output'), { recursive: true });
    fs.mkdirSync(path.join(googleDrivePath, 'output', 'thumbnails'), { recursive: true });
  } catch (err) {
    console.error(`⚠️ [Vite Config] No se pudieron crear carpetas en Google Drive: ${err.message}`);
  }
}

// Custom plugin to intercept YouTube/File requests, save them locally and trigger Colab
function localYoutubeDownloader() {
  return {
    name: 'local-youtube-downloader',
    configureServer(server) {
      // 1. Servir archivos locales desde Google Drive o el directorio de salida local si estan disponibles (evita descargar por Tailscale)
      server.middlewares.use(async (req, res, next) => {
        const googleDrivePath = process.env.GOOGLE_DRIVE_PATH;
        const localOutputDir = path.join(process.cwd(), '..', 'output');

        if (req.url.startsWith('/videos/')) {
          const relativePath = req.url.slice('/videos/'.length); // job_id/filename.mp4
          let localFilePath = '';
          if (googleDrivePath) {
            localFilePath = path.join(googleDrivePath, 'output', relativePath);
          }
          if (!localFilePath || !fs.existsSync(localFilePath)) {
            localFilePath = path.join(localOutputDir, relativePath);
          }

          if (fs.existsSync(localFilePath) && fs.statSync(localFilePath).isFile()) {
            console.log(`⚡ [Vite Local Server] Sirviendo video localmente: ${localFilePath}`);
            res.writeHead(200, { 'Content-Type': 'video/mp4' });
            fs.createReadStream(localFilePath).pipe(res);
            return;
          }
        }

        if (req.url.startsWith('/thumbnails/')) {
          const relativePath = req.url.slice('/thumbnails/'.length); // filename.png
          let localFilePath = '';
          if (googleDrivePath) {
            localFilePath = path.join(googleDrivePath, 'output', 'thumbnails', relativePath);
          }
          if (!localFilePath || !fs.existsSync(localFilePath)) {
            localFilePath = path.join(localOutputDir, 'thumbnails', relativePath);
          }

          if (fs.existsSync(localFilePath) && fs.statSync(localFilePath).isFile()) {
            console.log(`⚡ [Vite Local Server] Sirviendo miniatura localmente: ${localFilePath}`);
            let contentType = 'image/jpeg';
            if (relativePath.endsWith('.png')) contentType = 'image/png';
            else if (relativePath.endsWith('.gif')) contentType = 'image/gif';
            else if (relativePath.endsWith('.webp')) contentType = 'image/webp';
            
            res.writeHead(200, { 'Content-Type': contentType });
            fs.createReadStream(localFilePath).pipe(res);
            return;
          }
        }

        // Endpoint para abrir carpeta local en Explorer
        if (req.url === '/api/open-folder' && req.method === 'POST') {
          try {
            const bodyStr = await new Promise((resolve, reject) => {
              let data = '';
              req.on('data', chunk => data += chunk);
              req.on('end', () => resolve(data));
              req.on('error', err => reject(err));
            });
            const parsed = JSON.parse(bodyStr);
            const jobId = parsed.job_id;
            
            let folderPath = '';
            if (googleDrivePath) {
              folderPath = path.join(googleDrivePath, 'output', jobId);
            } else {
              folderPath = path.join(localOutputDir, jobId);
            }

            if (fs.existsSync(folderPath)) {
              console.log(`📂 [Vite Local Server] Abriendo carpeta en Explorer: ${folderPath}`);
              exec(`explorer "${folderPath}"`, (err) => {
                if (err) {
                  console.error(`Error al abrir explorador: ${err.message}`);
                }
              });
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ success: true, path: folderPath }));
            } else {
              console.warn(`⚠️ [Vite Local Server] Carpeta no existe aún: ${folderPath}`);
              res.writeHead(404, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ detail: `La carpeta local todavía no existe o está siendo sincronizada.` }));
            }
          } catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ detail: `Error: ${err.message}` }));
          }
          return;
        }

        next();
      });

      // 2. Interceptador de procesamiento /api/process
      server.middlewares.use(async (req, res, next) => {
        if (req.url === '/api/process' && req.method === 'POST') {
          const googleDrivePath = process.env.GOOGLE_DRIVE_PATH;
          const contentType = req.headers['content-type'] || '';

          // Caso A: Subida de archivo local multipart (usando Google Drive)
          if (googleDrivePath && contentType.includes('multipart/form-data')) {
            console.log(`\n==========================================================`);
            console.log(`📥 [Vite Local Downloader] Subida local detectada.`);
            console.log(`📥 [Vite Local Downloader] Guardando archivo directamente en tu Google Drive...`);
            console.log(`==========================================================`);

            try {
              const busboy = Busboy({ headers: req.headers });
              let uploadedFilename = '';
              let acknowledgedVal = 'false';
              let autoEditVal = 'false';
              const uniqueId = Date.now();
              let targetFilePath = '';
              let uploadPromise = null;

              busboy.on('file', (name, file, info) => {
                const { filename } = info;
                uploadedFilename = `upload_${uniqueId}_${filename}`;
                targetFilePath = path.join(googleDrivePath, 'uploads', uploadedFilename);
                console.log(`📥 [Vite Local Downloader] Escribiendo en: ${targetFilePath}`);

                const writeStream = fs.createWriteStream(targetFilePath);
                uploadPromise = new Promise((resolveStream, rejectStream) => {
                  file.pipe(writeStream);
                  writeStream.on('finish', resolveStream);
                  writeStream.on('error', rejectStream);
                });
              });

              busboy.on('field', (name, val) => {
                if (name === 'acknowledged') acknowledgedVal = val;
                if (name === 'auto_edit') autoEditVal = val;
              });

              busboy.on('finish', async () => {
                try {
                  if (uploadPromise) {
                    await uploadPromise;
                  }
                  const stats = fs.statSync(targetFilePath);
                  console.log(`✅ [Vite Local Downloader] Guardado en Drive! (${(stats.size / (1024 * 1024)).toFixed(2)} MB)`);
                  console.log(`📤 [Vite Local Downloader] Notificando a Colab para procesar (${BACKEND_URL})...`);

                  const response = await fetch(`${BACKEND_URL}/api/process`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'X-Gemini-Key': req.headers['x-gemini-key'] || '',
                    },
                    body: JSON.stringify({
                      drive_filename: uploadedFilename,
                      acknowledged: acknowledgedVal === 'true',
                      auto_edit: autoEditVal === 'true',
                      output_format: 'vertical'
                    })
                  });

                  const responseData = await response.json();
                  if (response.status >= 200 && response.status < 300) {
                    console.log(`🚀 [Vite Local Downloader] Job registrado en Colab: ${responseData.job_id}`);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify(responseData));
                  } else {
                    throw new Error(responseData.detail || `HTTP ${response.status}`);
                  }
                } catch (err) {
                  console.error(`❌ [Vite Local Downloader] Error procesando subida a Drive: ${err.message}`);
                  res.writeHead(500, { 'Content-Type': 'application/json' });
                  res.end(JSON.stringify({ detail: `Error procesando subida de archivo a Google Drive: ${err.message}` }));
                }
              });

              req.pipe(busboy);
            } catch (err) {
              console.error(`❌ [Vite Local Downloader] Error inicializando busboy: ${err.message}`);
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ detail: `Error inicializando busboy: ${err.message}` }));
            }
            return;
          }

          // Caso B: Peticiones JSON (YouTube URL o reenvio de endpoints)
          if (contentType.includes('application/json')) {
            try {
              const bodyStr = await new Promise((resolve, reject) => {
                let data = '';
                req.on('data', chunk => data += chunk);
                req.on('end', () => resolve(data));
                req.on('error', err => reject(err));
              });

              const parsed = JSON.parse(bodyStr);
              const url = parsed.url;

              if (url && (url.includes('youtube.com') || url.includes('youtu.be'))) {
                console.log(`\n==========================================================`);
                console.log(`📥 [Vite Local Downloader] YouTube URL Detectada: ${url}`);
                console.log(`📥 [Vite Local Downloader] Descargando video localmente para evitar bloqueo de YouTube...`);
                console.log(`==========================================================`);

                const uniqueId = Date.now();
                let tempFile = '';
                let uploadsDir = '';

                if (googleDrivePath) {
                  uploadsDir = path.join(googleDrivePath, 'uploads');
                  tempFile = path.join(uploadsDir, `local_dl_${uniqueId}.mp4`);
                } else {
                  const tempDir = path.join(process.cwd(), 'temp_downloads');
                  fs.mkdirSync(tempDir, { recursive: true });
                  tempFile = path.join(tempDir, `local_dl_${uniqueId}.mp4`);
                }

                // Cookies setup
                const parentCookies = path.join(process.cwd(), '..', 'cookies.txt');
                const localCookies = path.join(process.cwd(), 'cookies.txt');
                let cookiesPath = '';
                if (fs.existsSync(parentCookies)) {
                  cookiesPath = parentCookies;
                  console.log(`🍪 [Vite Local Downloader] Usando cookies encontradas en: ${parentCookies}`);
                } else if (fs.existsSync(localCookies)) {
                  cookiesPath = localCookies;
                  console.log(`🍪 [Vite Local Downloader] Usando cookies encontradas en: ${localCookies}`);
                }

                const args = [];
                if (cookiesPath) {
                  args.push('--cookies', cookiesPath);
                }
                args.push('-f', 'bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/bestvideo[vcodec^=avc1]+bestaudio/best[ext=mp4]/best');
                args.push('--merge-output-format', 'mp4');
                args.push('-o', tempFile);
                args.push(url);

                console.log(`📥 [Vite Local Downloader] Iniciando descarga con yt-dlp...`);

                const ytProcess = spawn('yt-dlp', args, { shell: true });
                let ytError = '';
                let lastDownloadPercent = -1;

                ytProcess.stdout.on('data', (data) => {
                  const output = data.toString();
                  const match = output.match(/\[download\]\s+(\d+(?:\.\d+)?)%/);
                  if (match) {
                    const percent = Math.floor(parseFloat(match[1]));
                    if (percent !== lastDownloadPercent && percent % 5 === 0) {
                      lastDownloadPercent = percent;
                      process.stdout.write(`\r📥 [Vite Local Downloader] Descargando de YouTube: ${percent}%`);
                    }
                  } else if (output.includes('[Merger]')) {
                    console.log(`\n🔄 [Vite Local Downloader] Combinando pistas de video y audio en un MP4 compatible...`);
                  }
                });

                ytProcess.stderr.on('data', (data) => {
                  ytError += data.toString();
                });

                ytProcess.on('close', async (code) => {
                  if (code !== 0) {
                    console.error(`\n❌ [Vite Local Downloader] Error al descargar: code ${code}. Detalle: ${ytError}`);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ detail: `Error al descargar video de YouTube: ${ytError || 'Proceso fallido'}.` }));
                    return;
                  }

                  console.log('');

                  if (!fs.existsSync(tempFile)) {
                    console.error(`❌ [Vite Local Downloader] Archivo descargado no encontrado.`);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ detail: `El video se descargo pero no se encontro el archivo temporal.` }));
                    return;
                  }

                  const stats = fs.statSync(tempFile);
                  
                  if (googleDrivePath) {
                    console.log(`\n==========================================================`);
                    console.log(`✅ [Vite Local Downloader] Descarga completa! (${(stats.size / (1024 * 1024)).toFixed(2)} MB)`);
                    console.log(`📤 [Vite Local Downloader] Registrando video de Google Drive en Colab (${BACKEND_URL})...`);
                    console.log(`==========================================================`);

                    try {
                      const response = await fetch(`${BACKEND_URL}/api/process`, {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                          'X-Gemini-Key': req.headers['x-gemini-key'] || '',
                        },
                        body: JSON.stringify({
                          drive_filename: `local_dl_${uniqueId}.mp4`,
                          acknowledged: parsed.acknowledged ? true : false,
                          auto_edit: !!parsed.auto_edit,
                          output_format: parsed.output_format || 'vertical'
                        })
                      });

                      const responseData = await response.json();
                      if (response.status >= 200 && response.status < 300) {
                        console.log(`🚀 [Vite Local Downloader] Registro exitoso! Job ID en Colab: ${responseData.job_id}`);
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify(responseData));
                      } else {
                        throw new Error(responseData.detail || `HTTP ${response.status}`);
                      }
                    } catch (colabErr) {
                      console.error(`❌ [Vite Local Downloader] Error registrando en Colab: ${colabErr.message}`);
                      res.writeHead(500, { 'Content-Type': 'application/json' });
                      res.end(JSON.stringify({ detail: `Error al registrar el video en Google Colab: ${colabErr.message}` }));
                    }
                  } else {
                    console.log(`\n==========================================================`);
                    console.log(`✅ [Vite Local Downloader] Descarga completa! (${(stats.size / (1024 * 1024)).toFixed(2)} MB)`);
                    console.log(`📤 [Vite Local Downloader] Subiendo video a Google Colab (${BACKEND_URL})...`);
                    console.log(`==========================================================`);

                    try {
                      const responseData = await new Promise((resolveUpload, rejectUpload) => {
                        const boundary = `----WebKitFormBoundary${Math.random().toString(36).substring(2)}`;
                        const header = `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="youtube_video.mp4"\r\nContent-Type: video/mp4\r\n\r\n`;
                        const middle = `\r\n--${boundary}\r\nContent-Disposition: form-data; name="acknowledged"\r\n\r\n${parsed.acknowledged ? 'true' : 'false'}\r\n`;
                        const footer = `--${boundary}--\r\n`;

                        const fileStats = fs.statSync(tempFile);
                        const totalSize = Buffer.byteLength(header) + fileStats.size + Buffer.byteLength(middle) + Buffer.byteLength(footer);

                        const parsedUrl = new URL(`${BACKEND_URL}`);
                        const client = parsedUrl.protocol === 'https:' ? https : http;

                        const reqOptions = {
                          method: 'POST',
                          hostname: parsedUrl.hostname,
                          port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
                          path: '/api/process',
                          headers: {
                            'X-Gemini-Key': req.headers['x-gemini-key'] || '',
                            'Content-Type': `multipart/form-data; boundary=${boundary}`,
                            'Content-Length': totalSize
                          }
                        };

                        const uploadReq = client.request(reqOptions, (uploadRes) => {
                          let resData = '';
                          uploadRes.on('data', chunk => resData += chunk);
                          uploadRes.on('end', () => {
                            if (uploadRes.statusCode >= 200 && uploadRes.statusCode < 300) {
                              try {
                                resolveUpload(JSON.parse(resData));
                              } catch (e) {
                                rejectUpload(new Error(`Respuesta no es JSON valido: ${resData}`));
                              }
                            } else {
                              rejectUpload(new Error(resData || `HTTP ${uploadRes.statusCode}`));
                            }
                          });
                        });

                        uploadReq.on('error', (err) => rejectUpload(err));
                        uploadReq.write(header);

                        const fileStream = fs.createReadStream(tempFile);
                        let bytesSent = Buffer.byteLength(header);
                        let lastReportedPercent = -1;

                        fileStream.on('data', (chunk) => {
                          uploadReq.write(chunk);
                          bytesSent += chunk.length;
                          const percent = Math.floor((bytesSent / totalSize) * 100);
                          if (percent !== lastReportedPercent && percent % 5 === 0) {
                            lastReportedPercent = percent;
                            process.stdout.write(`\r📤 [Vite Local Downloader] Subiendo a Colab: ${percent}% (${(bytesSent / (1024 * 1024)).toFixed(2)} MB de ${(totalSize / (1024 * 1024)).toFixed(2)} MB)`);
                          }
                        });

                        fileStream.on('end', () => {
                          uploadReq.write(middle);
                          uploadReq.write(footer);
                          uploadReq.end();
                          console.log(`\n📤 [Vite Local Downloader] Subida finalizada en red. Esperando que Colab confirme el Job...`);
                        });
                      });

                      console.log(`🚀 [Vite Local Downloader] Subida exitosa! Job ID en Colab: ${responseData.job_id}`);
                      res.writeHead(200, { 'Content-Type': 'application/json' });
                      res.end(JSON.stringify(responseData));

                    } catch (uploadErr) {
                      console.error(`\n❌ [Vite Local Downloader] Error al subir a Colab: ${uploadErr.message}`);
                      res.writeHead(500, { 'Content-Type': 'application/json' });
                      res.end(JSON.stringify({ detail: `Error al subir el video descargado a Google Colab: ${uploadErr.message}` }));
                    } finally {
                      try {
                        if (fs.existsSync(tempFile)) {
                          fs.unlinkSync(tempFile);
                          console.log(`🧹 [Vite Local Downloader] Limpieza completada: archivo temporal eliminado.`);
                        }
                      } catch (cleanupErr) {
                        console.error(`⚠️ [Vite Local Downloader] No se pudo eliminar el archivo temporal: ${cleanupErr.message}`);
                      }
                    }
                  }
                });
                return;
              } else {
                // Forward original request
                try {
                  const response = await fetch(`${BACKEND_URL}/api/process`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'X-Gemini-Key': req.headers['x-gemini-key'] || '',
                    },
                    body: bodyStr
                  });
                  const responseData = await response.json();
                  res.writeHead(response.status, { 'Content-Type': 'application/json' });
                  res.end(JSON.stringify(responseData));
                  return;
                } catch (forwardErr) {
                  res.writeHead(500, { 'Content-Type': 'application/json' });
                  res.end(JSON.stringify({ detail: `Error forwarding request: ${forwardErr.message}` }));
                  return;
                }
              }
            } catch (err) {
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ detail: `Internal processing error: ${err.message}` }));
              return;
            }
          }
        }
        next();
      });
    }
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), localYoutubeDownloader()],
  server: {
    allowedHosts: [
      'reelsflow.app',
      'www.reelsflow.app'
    ],
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/videos': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/thumbnails': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/gallery': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/video': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/render': {
        target: RENDER_URL,
        changeOrigin: true,
      }
    }
  }
})
