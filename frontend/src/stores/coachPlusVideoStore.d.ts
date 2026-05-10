export interface UploadState {
    jobId: string;
    fileName: string;
    uploadProgressPercent: number;
    status: 'uploading' | 'completing' | 'waiting' | 'error';
    error: string | null;
}
export declare const useCoachPlusVideoStore: any;
