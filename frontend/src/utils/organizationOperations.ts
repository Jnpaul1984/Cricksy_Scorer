import { getErrorMessage } from '@/services/api';

type HttpError = { status?: number };

export function organizationOperationError(reason: unknown, subject: string): string {
  const status = (reason as HttpError | null)?.status;
  const detail = getErrorMessage(reason);

  if (status === 403) return `You do not have permission to manage this ${subject}.`;
  if (status === 404)
    return `This ${subject} was not found or is not available in this organization.`;
  if (status === 409)
    return detail || `This ${subject} changed or has retained history. Refresh and try again.`;
  if (status === 422)
    return detail || `The ${subject} details were not accepted. Review the fields and try again.`;
  if (reason instanceof TypeError)
    return 'The service could not be reached. Check your connection and try again.';
  return detail;
}
