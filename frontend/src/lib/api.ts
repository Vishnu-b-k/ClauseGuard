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
 * @returns The analysis task info (status, contract_id, task_id)
 */
export async function analyzeContract(file: File): Promise<{status: string, contract_id: string, task_id: string}> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<{status: string, contract_id: string, task_id: string}>('/api/v1/contracts/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
}

export async function checkContractStatus(taskId: string): Promise<{status: string, state: string, result?: PipelineResultResponse}> {
  const response = await apiClient.get<{status: string, state: string, result?: PipelineResultResponse}>(`/api/v1/contracts/${taskId}/status`);
  return response.data;
}
