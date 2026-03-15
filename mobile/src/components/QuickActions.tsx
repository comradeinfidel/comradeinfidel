import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { theme } from '../theme';

type QuickAction = {
  icon: string;
  label: string;
  prompt: string;
  color: string;
};

const QUICK_ACTIONS: QuickAction[] = [
  {
    icon: '₿',
    label: 'Bitcoin Price',
    prompt: 'What is the current price of Bitcoin? Show me the 24h change.',
    color: theme.colors.warning,
  },
  {
    icon: '📈',
    label: 'My Stocks',
    prompt: 'Show me my current stock positions and portfolio value.',
    color: theme.colors.success,
  },
  {
    icon: '🔮',
    label: 'Market News',
    prompt: 'Search for the latest stock market and crypto news today.',
    color: theme.colors.primaryLight,
  },
  {
    icon: '💳',
    label: 'Payments',
    prompt: 'Show me my recent payments.',
    color: theme.colors.accent,
  },
  {
    icon: '🚀',
    label: 'Top Movers',
    prompt: 'Search for today\'s top gaining and losing stocks.',
    color: theme.colors.danger,
  },
  {
    icon: '💼',
    label: 'Portfolio',
    prompt: 'Give me a full summary of my portfolio: stocks, crypto, and cash.',
    color: theme.colors.primaryLight,
  },
];

type Props = {
  onSelect: (prompt: string) => void;
};

export function QuickActions({ onSelect }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>Quick Actions</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
      >
        {QUICK_ACTIONS.map((action, index) => (
          <TouchableOpacity
            key={index}
            style={[styles.chip, { borderColor: action.color + '40' }]}
            onPress={() => onSelect(action.prompt)}
            activeOpacity={0.7}
          >
            <Text style={styles.chipIcon}>{action.icon}</Text>
            <Text style={[styles.chipLabel, { color: action.color }]}>
              {action.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingTop: 8,
  },
  label: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
    fontWeight: theme.font.weightSemibold,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    paddingHorizontal: 20,
    marginBottom: 10,
  },
  scroll: {
    paddingHorizontal: 16,
    gap: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.full,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    gap: 6,
  },
  chipIcon: {
    fontSize: 16,
  },
  chipLabel: {
    fontSize: theme.font.sizeSm,
    fontWeight: theme.font.weightSemibold,
  },
});
