import { useCurrentUser } from '@/auth';
import { PageHeader } from '@/components/shared/PageHeader';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { can, canViewOrganisationAnalytics } from '@/lib/permissions';
import { CategoryReportSection } from '../components/CategoryReportSection';
import { ContainerReportSection } from '../components/ContainerReportSection';
import { DemandReportSection } from '../components/DemandReportSection';
import { ItemReportSection } from '../components/ItemReportSection';

export function ReportsPage() {
  const user = useCurrentUser();
  const isClerk = user.role === 'clerk' && !user.is_superuser;
  const showContainers = can(user, 'report.containers');
  const showDemand = canViewOrganisationAnalytics(user);

  return (
    <>
      <PageHeader title="Reports" description={isClerk ? 'Profit for the containers you own.' : 'Profit and demand across your organisation.'} />
      <Tabs defaultValue="categories">
        <TabsList>
          <TabsTrigger value="categories">By category</TabsTrigger>
          {showContainers && <TabsTrigger value="containers">By container</TabsTrigger>}
          <TabsTrigger value="items">By item</TabsTrigger>
          {showDemand && <TabsTrigger value="demand">Demand</TabsTrigger>}
        </TabsList>
        <TabsContent value="categories"><CategoryReportSection /></TabsContent>
        {showContainers && <TabsContent value="containers"><ContainerReportSection /></TabsContent>}
        <TabsContent value="items"><ItemReportSection /></TabsContent>
        {showDemand && <TabsContent value="demand"><DemandReportSection /></TabsContent>}
      </Tabs>
    </>
  );
}
