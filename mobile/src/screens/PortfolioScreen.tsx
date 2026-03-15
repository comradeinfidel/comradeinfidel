import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
} from 'react-native';
import { theme } from '../theme';

type Position = {
  symbol: string;
  qty: number;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
};

type CryptoAccount = {
  name: string;
  currency: string;
  available_balance: string;
};

// We poll the backend's HTTP endpoint for portfolio data
const BASE_URL = __DEV__ ? 'http://localhost:8000' : 'https://your-server.com';

async function fetchPortfolioData() {
  const sendChat = async (prompt: string) => {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: prompt }],
      }),
    });
    return res.json();
  };

  const [stockResp, cryptoResp] = await Promise.all([
    sendChat('Get my stock account info and all positions. Return data only.'),
    sendChat('Get my crypto accounts. Return data only.'),
  ]);

  return { stockResp, cryptoResp };
}

function MetricCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, color ? { color } : {}]}>{value}</Text>
      {sub && <Text style={styles.metricSub}>{sub}</Text>}
    </View>
  );
}

export function PortfolioScreen() {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<{ stockResp?: any; cryptoResp?: any } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const result = await fetchPortfolioData();
      setData(result);
    } catch (e: any) {
      setError(e.message || 'Failed to load portfolio');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        style={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => load(true)}
            tintColor={theme.colors.primary}
          />
        }
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Portfolio</Text>
          <Text style={styles.headerSubtitle}>Stocks • Crypto</Text>
        </View>

        {!data && !loading && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>📊</Text>
            <Text style={styles.emptyText}>
              Pull down to refresh, or ask the AI assistant about your portfolio.
            </Text>
            <TouchableOpacity style={styles.loadBtn} onPress={() => load(false)}>
              <Text style={styles.loadBtnText}>Load Portfolio</Text>
            </TouchableOpacity>
          </View>
        )}

        {loading && (
          <View style={styles.loadingState}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
            <Text style={styles.loadingText}>Loading portfolio data...</Text>
          </View>
        )}

        {error && (
          <View style={styles.errorState}>
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity style={styles.loadBtn} onPress={() => load(false)}>
              <Text style={styles.loadBtnText}>Retry</Text>
            </TouchableOpacity>
          </View>
        )}

        {data && (
          <View style={styles.content}>
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>📈 Stocks</Text>
              <Text style={styles.sectionHint}>
                {data.stockResp?.response || 'Use the chat to get detailed stock info'}
              </Text>
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>₿ Crypto</Text>
              <Text style={styles.sectionHint}>
                {data.cryptoResp?.response || 'Use the chat to get detailed crypto info'}
              </Text>
            </View>
          </View>
        )}

        <View style={styles.tip}>
          <Text style={styles.tipText}>
            💡 Tip: Use the AI Chat tab for real-time portfolio analysis, trading, and more.
          </Text>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scroll: {
    flex: 1,
  },
  header: {
    padding: 24,
    paddingTop: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  headerTitle: {
    fontSize: theme.font.sizeXxl,
    fontWeight: theme.font.weightBold,
    color: theme.colors.textPrimary,
  },
  headerSubtitle: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textMuted,
    marginTop: 2,
  },
  emptyState: {
    alignItems: 'center',
    padding: 48,
    gap: 16,
  },
  emptyIcon: {
    fontSize: 56,
  },
  emptyText: {
    fontSize: theme.font.sizeMd,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
  },
  loadBtn: {
    backgroundColor: theme.colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: theme.radius.full,
  },
  loadBtnText: {
    color: '#FFFFFF',
    fontWeight: theme.font.weightSemibold,
    fontSize: theme.font.sizeMd,
  },
  loadingState: {
    alignItems: 'center',
    padding: 48,
    gap: 16,
  },
  loadingText: {
    color: theme.colors.textSecondary,
    fontSize: theme.font.sizeMd,
  },
  errorState: {
    alignItems: 'center',
    padding: 48,
    gap: 16,
  },
  errorText: {
    color: theme.colors.danger,
    fontSize: theme.font.sizeMd,
    textAlign: 'center',
  },
  content: {
    padding: 16,
    gap: 16,
  },
  section: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
    gap: 8,
  },
  sectionTitle: {
    fontSize: theme.font.sizeLg,
    fontWeight: theme.font.weightBold,
    color: theme.colors.textPrimary,
  },
  sectionHint: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
    lineHeight: 20,
  },
  metricCard: {
    backgroundColor: theme.colors.surfaceElevated,
    borderRadius: theme.radius.md,
    padding: 14,
    flex: 1,
  },
  metricLabel: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  metricValue: {
    fontSize: theme.font.sizeXl,
    fontWeight: theme.font.weightBold,
    color: theme.colors.textPrimary,
  },
  metricSub: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textMuted,
    marginTop: 2,
  },
  tip: {
    margin: 16,
    backgroundColor: theme.colors.primaryGlow,
    borderRadius: theme.radius.md,
    padding: 14,
    borderWidth: 1,
    borderColor: theme.colors.primary + '30',
  },
  tipText: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.primaryLight,
    lineHeight: 20,
  },
});
