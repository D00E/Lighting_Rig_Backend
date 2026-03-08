/** Archived upload, old hardcoded format to NOSQL firebase 
 * This reflects an earlier document-oriented ingestion pipeline
 * before the backend was redesigned around Postgres + object storage.
 * 
 * Project specific configurations have been removed
*/

const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

if (!process.env.FIREBASE_KEY_PATH) {
  throw new Error('FIREBASE_KEY_PATH environment variable is not set');
}
const serviceAccountPath = process.env.FIREBASE_KEY_PATH;

if (!process.env.FIREBASE_STORAGE_BUCKET) {
  throw new Error('FIREBASE_STORAGE_BUCKET environment variable is not set');
}

admin.initializeApp({
  credential: admin.credential.cert(serviceAccountPath),
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
});

const firestore = admin.firestore();
const bucket = admin.storage().bucket();

const dirPath = process.env.DESIGNS_DIR || "./sample_designs";

async function readMetadata(dir, gifBaseName) {
  const metaPath = path.join(dir, `${gifBaseName}_meta.json`);
  console.log(metaPath);
  try {
    const content = await fs.promises.readFile(metaPath, 'utf8');
    const json = JSON.parse(content);
    return {
      gif_name: json.gif_name || gifBaseName,
      num_frames: json.num_frames || 0,
      num_packets: json.num_packets || 0,
      creator: json.creator || "",
      description: json.description || ""
    };
  } catch (err) {
    console.warn(`No metadata found for ${gifBaseName}, using defaults.`, err.message);
    return {
      gif_name: gifBaseName,
      num_frames: 0,
      num_packets: 0,
      creator: "",
      description: ""
    };
  }
}

async function processGif(filePath) {
  const code = await generateUniqueCode(firestore, 6);

  try {
    const fileName = path.basename(filePath, '.gif');

    console.log(`Processing GIF: ${fileName}`);

    const metadata = await readMetadata(dirPath, fileName);

    const resizedGifPath = path.join(dirPath, `${fileName}_16x16.gif`);

    const gifUrl = await uploadGifToStorage(resizedGifPath, code, fileName);

    const gifDocRef = firestore.collection('newGifs').doc(code);

    await gifDocRef.set({
      callsign: code,
      name: metadata.gif_name,        
      creator: metadata.creator,        
      description: metadata.description,
      num_frames: metadata.num_frames,
      num_packets: metadata.num_packets,
      gifPath: gifUrl
    });

    console.log(`Created document for GIF: ${fileName}`);

    const chunkFolders = await fs.promises.readdir(dirPath);
    const chunkSubfolders = chunkFolders.filter(folder => fs.statSync(path.join(dirPath, folder)).isDirectory() && folder.startsWith('chunk'));

    const sortedChunkSubfolders = chunkSubfolders.sort((a, b) => {
      const chunkNumberA = parseInt(a.replace('chunk', ''), 10);
      const chunkNumberB = parseInt(b.replace('chunk', ''), 10);
      return chunkNumberA - chunkNumberB;
    });

    const chunksSubcollection = gifDocRef.collection('chunks');

    for (const chunkFolder of sortedChunkSubfolders) {
      const chunkFolderPath = path.join(dirPath, chunkFolder);
      const packetFiles = await fs.promises.readdir(chunkFolderPath);

      let chunkData = [];

      for (const packetFile of packetFiles) {
        if (packetFile.endsWith('.txt')) {
          const packetFilePath = path.join(chunkFolderPath, packetFile);
          const packetData = await fs.promises.readFile(packetFilePath, 'utf8');
          const packet = packetData.trim();

          if (packet) {
            chunkData.push(packet);
          }
        }
      }

      console.log(`Processing ${chunkFolder} with ${chunkData.length} packets.`);

      const chunkDocRef = chunksSubcollection.doc(chunkFolder);
      await chunkDocRef.set({
        packets: chunkData,
        chunkNumber: sortedChunkSubfolders.indexOf(chunkFolder) + 1 
      });

      console.log(`Uploaded ${chunkFolder} with ${chunkData.length} packets.`);
    }

    console.log(`Successfully uploaded GIF '${fileName}' with ${sortedChunkSubfolders.length} chunks.`);
  } catch (error) {
    console.error('Error processing GIF:', error);
  }
}

async function processAllGifs() {
  try {
    const files = await fs.promises.readdir(dirPath); // Read files asynchronously

    for (const file of files) {
      const ext = path.extname(file).toLowerCase();

      if (ext === '.gif' && !file.endsWith('_16x16.gif')) {
        const filePath = path.join(dirPath, file);
        await processGif(filePath);
      }
    }
  } catch (error) {
    console.error('Error processing GIFs:', error);
  }
}

function randomCode(length = 6) {
  const chars = [];
  for (let code = 32; code <= 126; code++) {
    const ch = String.fromCharCode(code);
    if (ch === '?' || ch === '@' || ch === '!' || ch === ',' || ch === '.') continue;
    chars.push(ch);
  }

  let result = '';
  for (let i = 0; i < length; i++) {
    const idx = Math.floor(Math.random() * chars.length);
    result += chars[idx];
  }
  return result;
}

async function generateUniqueCode(firestore, length = 6) {
  while (true) {
    const code = randomCode(length);
    const docRef = firestore.collection('gifCodes').doc(code);

    try {
      await docRef.create({
        createdAt: admin.firestore.FieldValue.serverTimestamp()
      });
      return code;
    } catch (err) {
      if (err.code === 6 || err.code === 'already-exists') {
        continue;
      }
      throw err;
    }
  }
}

async function uploadGifToStorage(localPath, code, gifBaseName) {
  const destination = `gifs/${code}_${gifBaseName}.gif`;

  const [file] = await bucket.upload(localPath, {
    destination,
    resumable: false,
    metadata: {
      contentType: 'image/gif',
      cacheControl: 'public, max-age=31536000',
    },
  });

  await file.makePublic();

  const publicUrl = `https://storage.googleapis.com/${bucket.name}/${file.name}`;
  console.log('Uploaded GIF to:', publicUrl);
  return publicUrl;
}

processAllGifs();