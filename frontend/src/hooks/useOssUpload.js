import OSS from "ali-oss";
import { useState } from "react";
import apiClient from "@/services/apiClient";

function getExtension(filename) {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx) : "";
}

function sanitizeEndpoint(endpoint) {
  return endpoint.replace(/^https?:\/\//, "");
}

export function useOssUpload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const uploadFile = async (file) => {
    setUploading(true);
    setProgress(0);
    try {
      const stsRes = await apiClient.get("/api/oss/sts-token");
      const {
        AccessKeyId,
        AccessKeySecret,
        SecurityToken,
        region,
        bucket,
        endpoint,
      } = stsRes.data;

      const client = new OSS({
        region,
        bucket,
        accessKeyId: AccessKeyId,
        accessKeySecret: AccessKeySecret,
        stsToken: SecurityToken,
        endpoint: sanitizeEndpoint(endpoint),
        secure: true,
      });

      const ext = getExtension(file.name);
      const dateDir = new Date().toISOString().slice(0, 10);
      const objectKey = `assets/${dateDir}/${crypto.randomUUID()}${ext}`;

      await client.multipartUpload(objectKey, file, {
        progress: (p) => {
          setProgress(Math.round((p || 0) * 100));
        },
      });

      const publicUrl = `https://${bucket}.${sanitizeEndpoint(endpoint)}/${objectKey}`;
      return { url: publicUrl, objectKey };
    } finally {
      setUploading(false);
    }
  };

  return { uploading, progress, uploadFile };
}

