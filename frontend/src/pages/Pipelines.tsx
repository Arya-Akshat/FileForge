import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { filesApi } from "@/lib/api";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils/dateUtils";

interface FileWithJobs {
  id: string;
  original_name: string;
  status: string;
  created_at: string;
}

const Pipelines = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState<FileWithJobs[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const data = await filesApi.listFiles();
        // Only show files that have been processed or are processing
        setFiles(data.filter((f: FileWithJobs) => f.status === 'processing' || f.status === 'ready'));
      } catch (error) {
        toast.error("Failed to load pipeline history");
      } finally {
        setIsLoading(false);
      }
    };

    fetchFiles();
  }, []);
  const getStatusVariant = (status: string) => {
    switch (status) {
      case "completed":
        return "default";
      case "running":
        return "secondary";
      case "failed":
        return "destructive";
      default:
        return "outline";
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 bg-background">
        <div className="max-w-7xl mx-auto p-8">
          <p className="text-muted-foreground">Loading pipelines...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-background">
      <div className="max-w-7xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Pipeline History</h1>
          <p className="text-muted-foreground mt-1">
            Files with processing pipelines
          </p>
        </div>

        <div className="space-y-4">
          {files.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">No processed files yet</p>
                <Button 
                  variant="outline" 
                  onClick={() => navigate('/upload')}
                  className="mt-4"
                >
                  Upload & Process Files
                </Button>
              </CardContent>
            </Card>
          ) : (
            files.map((file) => (
              <Card key={file.id} className="hover:shadow-hover transition-all">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-medium text-foreground">
                          {file.original_name}
                        </h3>
                        <Badge
                          variant={getStatusVariant(file.status)}
                          className="capitalize"
                        >
                          {file.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Created: {formatDate(file.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="gap-2"
                        onClick={() => navigate(`/file/${file.id}`)}
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Pipelines;
