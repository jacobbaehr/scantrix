// server.js

import cors from 'cors';
import express from 'express';
import path from 'path';
import fs from 'fs';
import { spawnSync } from 'child_process';

import { fileURLToPath } from 'url';

import * as GS3D from '@mkkellogg/gaussian-splats-3d';
console.log(Object.keys(GS3D));

// __dirname shim in ESM:
const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

// 1) Allow override so you can set FRONTEND_DIST in prod (e.g. Docker)
const distPath = process.env.FRONTEND_DIST
  ? process.env.FRONTEND_DIST
  : path.resolve(__dirname, '..', 'scantrix-ui-web', 'dist');

console.log('Using frontend dist at:', distPath);

// sanity‐check
if (!fs.existsSync(distPath)) {
  console.error(`Could not find frontend dist folder at ${distPath}`);
  process.exit(1);
}

const app = express();

// mount static assets under /assets
app.use('/assets', express.static(path.join(distPath, 'assets')));

app.use(cors({
  origin: 'http://localhost:5173',
  methods: ['GET','POST','OPTIONS'],
}));

// serve the SPA shell for any URL starting with /splats/<something>[/…]
app.get(
  /^\/splats\/[^/]+(?:\/.*)?$/,
  (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
  }
);

// where all your splat_storage dirs live
const STORAGE_ROOT = path.resolve(process.env.SPLAT_STORAGE_DIR);
// path to your converter script
const KSPLAT_SCRIPT = path.resolve(__dirname, 'create-ksplat.js');

app.post('/ksplats/:splatUuid', (req, res) => {
  const { splatUuid } = req.params;

  // 1) build the target directory
  const targetDir = path.join(STORAGE_ROOT, splatUuid);
  if (!fs.existsSync(targetDir)) {
    return res.status(404).json({ error: `Directory ${splatUuid} not found` });
  }

  // 2) hard-coded filename inside each splat_storage/<splatUuid>
  const inputFilename = `${splatUuid}.ply`;
  const inputPath     = path.join(targetDir, inputFilename);
  if (!fs.existsSync(inputPath)) {
    return res.status(404).json({ error: `File ${inputFilename} not found in ${splatUuid}` });
  }

  // 3) output name: same dir, different extension
  const outputFilename = `${splatUuid}.ksplat`;
  const outputPath     = path.join(targetDir, outputFilename);

  // 4) run the script
  const result = spawnSync(
    process.execPath,                         // your Node.js binary
    [KSPLAT_SCRIPT, inputPath, outputPath],   // args: [input, output]
    { stdio: 'inherit' }                      // pipe stdio so you see logs
  );

  if (result.error || result.status !== 0) {
    console.error('create-ksplat.js failed', result.error || `exit ${result.status}`);
    return res.status(500).json({ error: 'Conversion failed' });
  }

  // 5) success: let the client know where to fetch it
  res.json({
    message: 'Ksplat created successfully',
    path: `/splat_storage/${splatUuid}/${outputFilename}`
  });
});

app.get('/api/v1/splats/:splatUuid', (req, res) => {
  const { splatUuid } = req.params;
  const filePath = path.join(STORAGE_ROOT, splatUuid, `${splatUuid}.ksplat`);

  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    return res.status(404).json({ error: 'File not found' });
  }

  const stat = fs.statSync(filePath);
  const fileSize = stat.size;

  res
    .status(200)
    .set({
      'Content-Length': fileSize,
      'Accept-Ranges': 'bytes',
      'Content-Type': 'application/octet-stream',
      'Content-Disposition': `attachment; filename="${splatUuid}.ksplat"`
    });
  fs.createReadStream(filePath).pipe(res);
});

// start the server
const port = process.env.PORT || 8090;
const host = process.env.HOST || '127.0.0.1';
app.listen(port, host, () => {
  console.log(`🚀 Express server listening on http://${host}:${port}`);
});
