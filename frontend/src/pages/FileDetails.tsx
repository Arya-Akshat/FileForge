import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JobStatusBadge } from "@/components/JobStatusBadge";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Download, Trash2, Eye } from "lucide-react";
import { toast } from "sonner";
import { filesApi } from "@/lib/api";
import { formatDate } from "@/lib/utils/dateUtils";

interface File {
  id: string;
  original_name: string;
  size_bytes: number;
  mime_type: string;
  storage_key: string;
  status: string;
  created_at: string;
  download_url?: string;
}

interface Job {
  id: string;
  type: string;
  status: string;
  created_at: string;
  updated_at: string;
  result_file_id?: string;
  error_message?: string;
  params: Record<string, any>;
}

const FileDetails = () => {
  const navigate = useNavigate();
  const { fileId } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchFileDetails = async (isInitial = false) => {
      if (!fileId) return;
      
      if (isInitial) setIsLoading(true);
      try {
        const data = await filesApi.getFile(fileId);
        setFile(data as any);
        setJobs(data.jobs || []);
      } catch (error) {
        if (isInitial) {
          toast.error(error instanceof Error ? error.message : "Failed to load file details");
        }
      } finally {
        if (isInitial) setIsLoading(false);
      }
    };

    fetchFileDetails(true);
    const interval = setInterval(() => fetchFileDetails(false), 3000);
    return () => clearInterval(interval);
  }, [fileId]);

  const handleDelete = async () => {
    if (!fileId) return;
    
    if (!confirm("Are you sure you want to delete this file?")) return;

    try {
      await filesApi.deleteFile(fileId);
      toast.success("File deleted successfully");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to delete file");
    }
  };

  const handleDownload = async () => {
    if (!file) return;
    
    try {
      const token = localStorage.getItem('auth_token');
      const downloadUrl = `http://localhost/api/files/${file.id}/download`;
      
      const response = await fetch(downloadUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        // Try to parse error message
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const error = await response.json();
          throw new Error(error.detail || 'Download failed');
        }
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = file.original_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('File downloaded successfully');
    } catch (error) {
      console.error('Download error:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to download file');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
  };



  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
      case "ready":
        return "default";
      case "processing":
      case "pending":
        return "secondary";
      case "failed":
        return "destructive";
      default:
        return "outline";
    }
  };

  const getJobTypeLabel = (jobType: string) => {
    const labels: Record<string, string> = {
      thumbnail: "Thumbnail Generation",
      image_convert: "Image Conversion",
      image_compress: "Image Compression",
      video_thumbnail: "Video Thumbnail",
      video_preview: "Video Preview",
      video_convert: "Video Conversion",
      metadata: "Metadata Extraction",
      encrypt: "File Encryption",
      decrypt: "File Decryption",
      virus_scan: "Virus Scan",
      ai_tag: "AI Tagging",
    };
    return labels[jobType] || jobType;
  };

  if (isLoading) {
    return (
      <div className="flex-1 bg-background">
        <div className="max-w-7xl mx-auto p-8">
          <p className="text-muted-foreground">Loading file details...</p>
        </div>
      </div>
    );
  }

  if (!file) {
    return (
      <div className="flex-1 bg-background">
        <div className="max-w-7xl mx-auto p-8">
          <p className="text-destructive">File not found</p>
          <Button onClick={() => navigate("/dashboard")} className="mt-4">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-background">
      <div className="max-w-7xl mx-auto p-8">
        <Button
          variant="ghost"
          onClick={() => navigate("/dashboard")}
          className="mb-6 gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Files
        </Button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>File Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Filename</p>
                  <p className="font-medium">{file.original_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Size</p>
                  <p className="font-medium">{formatFileSize(file.size_bytes)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">MIME Type</p>
                  <p className="font-medium">{file.mime_type}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Uploaded</p>
                  <p className="font-medium">{formatDate(file.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Storage Key</p>
                  <p className="font-medium text-xs">{file.storage_key}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge variant={getStatusColor(file.status)} className="capitalize">
                    {file.status}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                className="w-full justify-start gap-2"
                onClick={() => navigate(`/file/${fileId}/results`)}
              >
                <Eye className="w-4 h-4" />
                View Results
              </Button>
              <Button 
                variant="outline" 
                className="w-full justify-start gap-2"
                onClick={handleDownload}
              >
                <Download className="w-4 h-4" />
                Download File
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start gap-2 text-destructive hover:text-destructive"
                onClick={handleDelete}
              >
                <Trash2 className="w-4 h-4" />
                Delete File
              </Button>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Processing Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {jobs.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">No processing jobs yet</p>
              ) : (
                jobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-4 border border-border rounded-lg"
                  >
                    <div className="flex-1">
                      <h3 className="font-medium text-foreground">{getJobTypeLabel(job.type)}</h3>
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span>Created: {formatDate(job.created_at)}</span>
                        <span>•</span>
                        <span>Updated: {formatDate(job.updated_at)}</span>
                      </div>
                      {job.error_message && (
                        <p className="text-sm text-destructive mt-1">{job.error_message}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      <JobStatusBadge status={job.status} />
                      {job.result_file_id && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => navigate(`/file/${job.result_file_id}`)}
                        >
                          View Output
                        </Button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FileDetails;
