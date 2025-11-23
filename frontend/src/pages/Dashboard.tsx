import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FileCard } from "@/components/FileCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Plus } from "lucide-react";
import { filesApi } from "@/lib/api";
import { toast } from "sonner";

const Dashboard = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [files, setFiles] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const data = await filesApi.listFiles();
      setFiles(data);
    } catch (error) {
      toast.error("Failed to load files");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (fileId: string) => {
    try {
      await filesApi.deleteFile(fileId);
      toast.success("File deleted");
      loadFiles();
    } catch (error) {
      toast.error("Failed to delete file");
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getFileType = (mimeType: string): "image" | "video" | "document" => {
    if (mimeType?.startsWith('image/')) return 'image';
    if (mimeType?.startsWith('video/')) return 'video';
    return 'document';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  const filteredFiles = files
    .filter((file) =>
      file.original_name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .map(file => ({
      id: file.id,
      fileName: file.original_name,
      size: formatFileSize(file.size_bytes),
      status: file.status as "ready" | "processing" | "uploaded" | "failed",
      createdAt: formatDate(file.created_at),
      fileType: getFileType(file.mime_type),
    }));

  return (
    <div className="flex-1 bg-background">
      <div className="max-w-7xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Files</h1>
            <p className="text-muted-foreground mt-1">
              Manage and process your files
            </p>
          </div>
          <Button onClick={() => navigate("/upload")} className="gap-2">
            <Plus className="w-4 h-4" />
            Upload File
          </Button>
        </div>

        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading files...</p>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {filteredFiles.map((file) => (
                <FileCard
                  key={file.id}
                  {...file}
                  onView={() => navigate(`/file/${file.id}`)}
                  onDownload={() => {
                    const originalFile = files.find(f => f.id === file.id);
                    if (originalFile?.download_url) {
                      window.open(originalFile.download_url, '_blank');
                    }
                  }}
                  onDelete={() => handleDelete(file.id)}
                />
              ))}
            </div>

            {filteredFiles.length === 0 && !isLoading && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">
                  {searchQuery ? 'No files found' : 'No files yet. Upload your first file!'}
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
