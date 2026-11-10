import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { compactMoney, formatMoney } from '@/lib/money';

export interface ChartSeries {
  key: string;
  label: string;
  color: string; // a CSS colour or design token, e.g. 'var(--primary)'
}

interface Props {
  title: string;
  /** read aloud by screen readers; the table under every chart carries the same numbers */
  description: string;
  data: Record<string, string | number>[];
  series: ChartSeries[];
  money?: boolean;
}

const shorten = (s: string): string => (s.length > 14 ? `${s.slice(0, 13)}...` : s);

export function BarChartCard({ title, description, data, series, money = true }: Props) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent>
        <div role="img" aria-label={description} className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="name" interval={0} tickFormatter={shorten} tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
              <YAxis width={64} tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} tickFormatter={(v: number) => (money ? compactMoney(v) : String(v))} axisLine={false} tickLine={false} />
              <Tooltip
                formatter={(value) => (money ? formatMoney(Number(value)) : String(value))}
                contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--foreground)' }}
                cursor={{ fill: 'var(--muted)', opacity: 0.5 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {series.map((s) => <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[4, 4, 0, 0]} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
