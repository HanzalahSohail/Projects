// utils/s3.js
const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');
const crypto = require('crypto');

const s3 = new S3Client({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

async function uploadBufferToS3(buffer, mimetype, folder = '') {
  const key =
    folder +
    crypto.randomBytes(8).toString('hex') +
    '__' +
    Date.now() +
    (mimetype.split('/')[1] === 'jpeg' ? '.jpg' : `.${mimetype.split('/')[1]}`);

  await s3.send(
    new PutObjectCommand({
      Bucket: process.env.S3_BUCKET,
      Key: key,
      Body: buffer,
      ContentType: mimetype,
      // ACL: 'public-read',        // or omit + use signed URLs
    })
  );

  return `https://${process.env.S3_BUCKET}.s3.${process.env.AWS_REGION}.amazonaws.com/${key}`;
}

module.exports = { uploadBufferToS3 };
