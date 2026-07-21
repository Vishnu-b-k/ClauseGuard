import axios from 'axios';
import { PipelineResultResponse } from '@/types';

// Ideally, this would be an environment variable.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

/**
 * Uploads a contract for analysis.
 * @param file The contract file (PDF, DOCX, TXT)
 * @returns The analysis pipeline result
 */
export async function analyzeContract(file: File): Promise<PipelineResultResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<PipelineResultResponse>('/api/v1/contracts/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
}
