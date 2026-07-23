import { apiClient } from './api';

/**
 * Internal helper to download a PDF from the backend and trigger browser download.
 *
 * @param url Backend endpoint URL (including any query parameters)
 * @param fallbackFilename Filename to use if Content-Disposition header is missing or cannot be parsed
 */
async function downloadPDF(url: string, fallbackFilename: string): Promise<void> {
  if (typeof window === 'undefined') {
    throw new Error('PDF download can only be initiated in a browser environment.');
  }

  try {
    const response = await apiClient.get(url, {
      responseType: 'blob',
    });

    const contentDisposition = response.headers['content-disposition'];
    let filename = fallbackFilename;

    if (contentDisposition) {
      // Extract filename from Content-Disposition header (e.g. attachment; filename=example.pdf)
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }

    // Create browser download link and trigger it
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();

    // Clean up DOM and revoke the object URL
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error: any) {
    if (error.response) {
      const status = error.response.status;
      if (status === 404) {
        throw new Error('Repository analysis not found. Please analyze the repository first.');
      } else if (status === 500) {
        throw new Error('Unable to generate PDF.');
      } else {
        throw new Error('Unable to generate PDF.');
      }
    } else {
      throw new Error('Unable to connect to backend.');
    }
  }
}

/**
 * Downloads the Repository Guide PDF.
 *
 * @param owner GitHub repository owner
 * @param repo GitHub repository name
 */
export async function downloadRepositoryGuide(owner: string, repo: string): Promise<void> {
  const url = `/pdf/repository?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}`;
  const fallbackFilename = `${repo.toLowerCase()}_repository_guide.pdf`;
  await downloadPDF(url, fallbackFilename);
}

/**
 * Downloads the Issue Guide PDF.
 *
 * @param owner GitHub repository owner
 * @param repo GitHub repository name
 * @param issueNumber GitHub issue number
 */
export async function downloadIssueGuide(
  owner: string,
  repo: string,
  issueNumber: number | string
): Promise<void> {
  const url = `/pdf/issue/${issueNumber}?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}`;
  const fallbackFilename = `${repo.toLowerCase()}_issue_${issueNumber}_guide.pdf`;
  await downloadPDF(url, fallbackFilename);
}

/**
 * Downloads the Contribution Guide PDF for a specific repository and optional issue.
 *
 * @param owner GitHub repository owner
 * @param repo GitHub repository name
 * @param issueNumber Optional GitHub issue number
 */
export async function downloadContributionGuide(
  owner: string,
  repo: string,
  issueNumber?: number | string
): Promise<void> {
  const issueQuery = issueNumber ? `&issue_number=${encodeURIComponent(issueNumber)}` : '';
  const url = `/pdf/contribution?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}${issueQuery}`;
  const fallbackFilename = issueNumber
    ? `${repo.toLowerCase()}_issue_${issueNumber}_contribution_guide.pdf`
    : `${repo.toLowerCase()}_contribution_guide.pdf`;
  await downloadPDF(url, fallbackFilename);
}
