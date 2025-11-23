import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Download, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { filesApi } from "@/lib/api";
import { formatDate } from "@/lib/utils/dateUtils";

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

interface File {
  id: string;
  original_name: string;
  size_bytes: number;
  mime_type: string;
  status: string;
  created_at: string;
  download_url?: string;
  ai_tags?: string[];
}

interface ProcessedFile {
  id: string;
  original_name: string;
  size_bytes: number;
  mime_type: string;
  status: string;
  created_at: string;
  download_url?: string;
}

const Results = () => {
  const navigate = useNavigate();
  const { fileId } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [processedFiles, setProcessedFiles] = useState<ProcessedFile[]>([]);

  useEffect(() => {
    const fetchResults = async () => {
      if (!fileId) return;
      
      setIsLoading(true);
      try {
        const data = await filesApi.getFile(fileId);
        console.log('Results page - Received data:', data);
        console.log('Results page - AI tags:', data.ai_tags);
        setFile(data as any);
        // Show all jobs (including virus scan)
        setJobs(data.jobs || []);
        setProcessedFiles(data.processed_outputs || []);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Failed to load results");
      } finally {
        setIsLoading(false);
      }
    };

    fetchResults();
    
    // Poll for updates every 3 seconds
    const interval = setInterval(fetchResults, 3000);
    
    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, [fileId]);

  const getJobTypeLabel = (jobType: string): string => {
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

  const handleDownloadOutput = async (outputPath: string) => {
    try {
      // Construct download URL for output file
      const downloadUrl = `${import.meta.env.VITE_API_URL || 'http://localhost/api'}/files/download/${outputPath}`;
      window.open(downloadUrl, "_blank");
    } catch (error) {
      toast.error("Failed to download output");
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 bg-background">
        <div className="max-w-7xl mx-auto p-8">
          <p className="text-muted-foreground">Loading results...</p>
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
          onClick={() => navigate(`/file/${fileId}`)}
          className="mb-6 gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to File Details
        </Button>

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Processed Results</h1>
            <p className="text-muted-foreground mt-1">
              {file.original_name} - {processedFiles.length} processed output{processedFiles.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        {/* Job Results Section (for virus scan, etc.) */}
        {jobs.filter(j => j.error_message && j.type === 'virus_scan').length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Scan Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {jobs.filter(j => j.error_message && j.type === 'virus_scan').map((job) => (
                  <div key={job.id} className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                    <Badge variant={job.status === 'COMPLETED' ? 'default' : 'destructive'}>
                      {getJobTypeLabel(job.type)}
                    </Badge>
                    <span className="text-sm">{job.error_message}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* AI Tags Section */}
        {file.ai_tags && file.ai_tags.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>AI Generated Tags</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {file.ai_tags.map((tag, index) => (
                  <Badge key={index} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {processedFiles.length === 0 && (!file.ai_tags || file.ai_tags.length === 0) ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">No processed outputs or AI tags available yet</p>
              <p className="text-sm text-muted-foreground mt-2">
                {jobs.length > 0 ? 'Jobs are still processing...' : 'No processing jobs were requested'}
              </p>
              <Button
                variant="outline"
                onClick={() => navigate(`/file/${fileId}`)}
                className="mt-4"
              >
                Back to File Details
              </Button>
            </CardContent>
          </Card>
        ) : processedFiles.length > 0 ? (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Processed Files</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {processedFiles.map((pf) => (
                    <div
                      key={pf.id}
                      className="flex items-center justify-between p-4 border border-border rounded-lg"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-foreground">{pf.original_name}</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          Size: {(pf.size_bytes / 1024).toFixed(2)} KB • Type: {pf.mime_type}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Created: {formatDate(pf.created_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="default">{pf.status}</Badge>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="gap-2"
                          onClick={() => navigate(`/file/${pf.id}`)}
                        >
                          <Download className="w-4 h-4" />
                          Download
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default Results;
