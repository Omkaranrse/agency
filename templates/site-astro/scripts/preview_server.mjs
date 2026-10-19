import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.resolve(__dirname, '..', 'dist');
const port = parseInt(process.env.PORT || '4321', 10);

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
};

const server = http.createServer((req, res) => {
  let reqPath = decodeURI(req.url.split('?')[0]);
  if (reqPath.endsWith('/')) {
    reqPath += 'index.html';
  } else if (!path.extname(reqPath)) {
    if (fs.existsSync(path.join(distDir, reqPath, 'index.html'))) {
      reqPath = path.join(reqPath, 'index.html');
    } else {
      reqPath += '.html';
    }
  }

  const filePath = path.join(distDir, reqPath);
  if (!filePath.startsWith(distDir)) {
    res.statusCode = 403;
    res.end('Forbidden');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.statusCode = 404;
      res.end('Not Found');
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = mimeTypes[ext] || 'application/octet-stream';
    res.setHeader('Content-Type', contentType);
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(port, '0.0.0.0', () => {
  console.log(`Preview server running at http://localhost:${port}/`);
});

const pidFile = path.resolve(__dirname, '..', '.preview.pid');
fs.writeFileSync(pidFile, String(process.pid));

function cleanup() {
  try {
    if (fs.existsSync(pidFile)) fs.unlinkSync(pidFile);
  } catch (_) {}
  server.close(() => {
    process.exit(0);
  });
}

process.on('SIGTERM', cleanup);
process.on('SIGINT', cleanup);
