import { getServerSession } from "@/lib/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield } from "lucide-react";

export default async function DashboardPage() {
  const user = await getServerSession();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back, {user?.username}. Here&apos;s an overview of your security posture.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Platform Status</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Milestone 1</div>
            <p className="text-xs text-muted-foreground">Setup Complete</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-muted/50 border-dashed">
        <CardHeader>
          <CardTitle>Milestone 1 Complete</CardTitle>
          <CardDescription>
            Data will appear after Milestone 3 connector setup is finalized.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The foundational UI and authentication systems are operational. Once data sources are connected, this dashboard will populate with live intelligence.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
