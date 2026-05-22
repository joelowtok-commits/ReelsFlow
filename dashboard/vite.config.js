import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { exec, spawn } from 'child_process'
import fs from 'fs'
import path from 'path'
import os from 'os'
import http from 'http'
import https from 'https'

// Backend URL: defaults to localhost for local dev.
// Set VITE_BACKEND_URL=http://100.x.x.x:8000 to point to Kaggle/Colab GPU.
const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://localhost:8000'
const RENDER_URL = process.env.VITE_RENDER_URL || 'http://localhost:3100'

// Custom plugin to intercept YouTube requests, download them locally and upload them to Colab
function localYoutubeDownloader() {
  return {
    name: 'local-youtube-downloader',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.url === '/api/process' && req.method === 'POST') {
          const contentType = req.headers['content-type'] || '';
          if (contentType.includes('application/json')) {
            try {
              // Read body
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

                // Create a temporary downloads folder inside the project to ensure clean permissions
                const tempDir = path.join(process.cwd(), 'temp_downloads');
                fs.mkdirSync(tempDir, { recursive: true });
                const uniqueId = Date.now();
                const tempFile = path.join(tempDir, `local_dl_${uniqueId}.mp4`);

                // Look for cookies.txt in parent directory or current directory
                const parentCookies = path.join(process.cwd(), '..', 'cookies.txt');
                const localCookies = path.join(process.cwd(), 'cookies.txt');
                let cookiesPath = '';
                if (fs.existsSync(parentCookies)) {
                  cookiesPath = parentCookies;
                  console.log(`🍪 [Vite Local Downloader] Usando cookies encontradas en: ${parentCookies}`);
                } else if (fs.existsSync(localCookies)) {
                  cookiesPath = localCookies;
                  console.log(`🍪 [Vite Local Downloader] Usando cookies encontradas en: ${localCookies}`);
                } else {
                  console.log(`⚠️ [Vite Local Downloader] No se encontro cookies.txt. Si YouTube te bloquea, crea un cookies.txt en la raiz.`);
                }

                // Run yt-dlp locally on Windows using spawn to capture real-time progress
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
                  // Extract progress percentage from yt-dlp output, e.g., "[download]  10.2% of ~15.22MiB"
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

                  // Force a newline after writing with \r
                  console.log('');

                  if (!fs.existsSync(tempFile)) {
                    console.error(`❌ [Vite Local Downloader] Archivo descargado no encontrado.`);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ detail: `El video se descargo pero no se encontro el archivo temporal.` }));
                    return;
                  }

                  const stats = fs.statSync(tempFile);
                  console.log(`\n==========================================================`);
                  console.log(`✅ [Vite Local Downloader] Descarga completa! (${(stats.size / (1024 * 1024)).toFixed(2)} MB)`);
                  console.log(`📤 [Vite Local Downloader] Subiendo video a Google Colab (${BACKEND_URL})...`);
                  console.log(`==========================================================`);

                  // Perform upload with progress tracking using native http/https request
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

                      // Write the leading boundary header
                      uploadReq.write(header);

                      // Stream the actual file with progress tracking
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
                    // Clean up temp file
                    try {
                      if (fs.existsSync(tempFile)) {
                        fs.unlinkSync(tempFile);
                        console.log(`🧹 [Vite Local Downloader] Limpieza completada: archivo temporal eliminado.`);
                      }
                    } catch (cleanupErr) {
                      console.error(`⚠️ [Vite Local Downloader] No se pudo eliminar el archivo temporal: ${cleanupErr.message}`);
                    }
                  }
                });

                return;
              } else {
                // It is a JSON request but not a YouTube URL
                // Forward it manually
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
  }
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
