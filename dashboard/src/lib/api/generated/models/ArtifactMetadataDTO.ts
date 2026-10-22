/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Safe metadata describing an available run artifact.
 */
export type ArtifactMetadataDTO = {
    /**
     * Unique artifact identifier
     */
    artifact_id: string;
    /**
     * Approved category of artifact
     */
    artifact_type: string;
    created_at?: string;
    /**
     * User-facing artifact filename
     */
    display_name: string;
    /**
     * True if raw file can be downloaded
     */
    download_available?: boolean;
    /**
     * Content MIME type
     */
    mime_type: string;
    /**
     * Associated run identifier
     */
    run_id: string;
    /**
     * Size in bytes
     */
    size_bytes?: (number | null);
};
