import { useState } from "react";
import { uploadDocuments, UploadResponse } from "../api/upload";

export function useUpload() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  async function upload(
    files: File[],
    token?: string
  ) {
    try {
      setLoading(true);
      setProgress(10);
      setError(null);

      const timer = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 300);

      const response = await uploadDocuments(files, token);

      clearInterval(timer);

      setProgress(100);
      setResult(response);

      return response;

    } catch (err: any) {

      setError(err.message ?? "Upload failed");

      throw err;

    } finally {

      setLoading(false);

    }
  }

  function reset() {
    setLoading(false);
    setProgress(0);
    setError(null);
    setResult(null);
  }

  return {
    upload,
    loading,
    progress,
    error,
    result,
    reset,
  };
}