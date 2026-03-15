import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { theme } from '../theme';

export type MessageStatus = 'sending' | 'streaming' | 'done' | 'error';

export type ToolEvent = {
  tool_name: string;
  status: 'running' | 'done';
  result?: Record<string, unknown>;
};

export type MessageData = {
  id: string;
  role: 'user' | 'assistant' | 'thinking';
  content: string;
  status?: MessageStatus;
  toolEvents?: ToolEvent[];
  thinking?: string;
};

const TOOL_ICONS: Record<string, string> = {
  web_search: '🔍',
  web_fetch: '🌐',
  send_payment: '💳',
  get_payment_status: '💰',
  list_recent_payments: '📊',
  get_stock_quote: '📈',
  get_stock_account: '🏦',
  get_stock_positions: '📋',
  buy_stock: '🟢',
  sell_stock: '🔴',
  get_stock_orders: '📑',
  get_crypto_price: '₿',
  get_crypto_accounts: '🔐',
  buy_crypto: '🚀',
  sell_crypto: '📉',
  get_crypto_orders: '📜',
};

const TOOL_LABELS: Record<string, string> = {
  web_search: 'Searching the web',
  web_fetch: 'Fetching page',
  send_payment: 'Sending payment',
  get_payment_status: 'Checking payment',
  list_recent_payments: 'Loading payments',
  get_stock_quote: 'Getting quote',
  get_stock_account: 'Loading account',
  get_stock_positions: 'Loading positions',
  buy_stock: 'Placing buy order',
  sell_stock: 'Placing sell order',
  get_stock_orders: 'Loading orders',
  get_crypto_price: 'Getting crypto price',
  get_crypto_accounts: 'Loading crypto accounts',
  buy_crypto: 'Buying crypto',
  sell_crypto: 'Selling crypto',
  get_crypto_orders: 'Loading crypto orders',
};

function ToolEventPill({ event }: { event: ToolEvent }) {
  const icon = TOOL_ICONS[event.tool_name] || '⚙️';
  const label = TOOL_LABELS[event.tool_name] || event.tool_name;
  const isRunning = event.status === 'running';

  return (
    <View style={[styles.toolPill, isRunning && styles.toolPillRunning]}>
      <Text style={styles.toolIcon}>{icon}</Text>
      <Text style={styles.toolLabel}>{label}</Text>
      {isRunning && (
        <ActivityIndicator size="small" color={theme.colors.accent} style={{ marginLeft: 6 }} />
      )}
      {!isRunning && (
        <Text style={styles.toolDone}>✓</Text>
      )}
    </View>
  );
}

export function MessageBubble({ message }: { message: MessageData }) {
  const isUser = message.role === 'user';
  const isThinking = message.role === 'thinking';

  if (isThinking && !message.thinking) return null;

  return (
    <View style={[styles.container, isUser && styles.containerUser]}>
      {!isUser && (
        <View style={styles.avatarContainer}>
          <Text style={styles.avatar}>✦</Text>
        </View>
      )}

      <View style={[styles.bubbleWrapper, isUser && styles.bubbleWrapperUser]}>
        {/* Thinking block */}
        {message.thinking && (
          <View style={styles.thinkingBubble}>
            <Text style={styles.thinkingLabel}>💭 Thinking</Text>
            <Text style={styles.thinkingText} numberOfLines={3}>
              {message.thinking}
            </Text>
          </View>
        )}

        {/* Tool events */}
        {message.toolEvents && message.toolEvents.length > 0 && (
          <View style={styles.toolEvents}>
            {message.toolEvents.map((evt, i) => (
              <ToolEventPill key={i} event={evt} />
            ))}
          </View>
        )}

        {/* Main bubble */}
        {message.content.length > 0 && (
          <View style={[
            styles.bubble,
            isUser ? styles.userBubble : styles.aiBubble,
            isThinking && styles.thinkingBubbleMain,
          ]}>
            <Text style={[
              styles.messageText,
              isUser ? styles.userText : styles.aiText,
            ]}>
              {message.content}
            </Text>
            {message.status === 'streaming' && (
              <View style={styles.cursor} />
            )}
          </View>
        )}

        {/* Loading indicator when waiting */}
        {message.status === 'sending' && message.content.length === 0 && (
          <View style={[styles.bubble, styles.aiBubble, styles.loadingBubble]}>
            <View style={styles.typingDots}>
              <View style={[styles.dot, styles.dot1]} />
              <View style={[styles.dot, styles.dot2]} />
              <View style={[styles.dot, styles.dot3]} />
            </View>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: 6,
    paddingHorizontal: 16,
    alignItems: 'flex-end',
  },
  containerUser: {
    flexDirection: 'row-reverse',
  },
  avatarContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: theme.colors.primaryDark,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
    marginBottom: 2,
  },
  avatar: {
    fontSize: 14,
    color: theme.colors.primaryLight,
  },
  bubbleWrapper: {
    maxWidth: '80%',
    alignItems: 'flex-start',
  },
  bubbleWrapperUser: {
    alignItems: 'flex-end',
  },
  bubble: {
    borderRadius: theme.radius.lg,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginTop: 2,
  },
  userBubble: {
    backgroundColor: theme.colors.userBubble,
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: theme.colors.aiBubble,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  thinkingBubbleMain: {
    backgroundColor: theme.colors.thinkingBubble,
    borderColor: theme.colors.borderLight,
  },
  messageText: {
    fontSize: theme.font.sizeMd,
    lineHeight: 22,
  },
  userText: {
    color: '#FFFFFF',
    fontWeight: theme.font.weightMedium,
  },
  aiText: {
    color: theme.colors.textPrimary,
  },
  cursor: {
    width: 2,
    height: 16,
    backgroundColor: theme.colors.primaryLight,
    borderRadius: 1,
    marginTop: 2,
    opacity: 0.8,
  },
  loadingBubble: {
    paddingVertical: 16,
    paddingHorizontal: 20,
  },
  typingDots: {
    flexDirection: 'row',
    gap: 5,
    alignItems: 'center',
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: theme.colors.textSecondary,
    opacity: 0.6,
  },
  dot1: {},
  dot2: { opacity: 0.8 },
  dot3: { opacity: 1 },
  thinkingBubble: {
    backgroundColor: theme.colors.thinkingBubble,
    borderRadius: theme.radius.md,
    padding: 10,
    marginBottom: 4,
    borderWidth: 1,
    borderColor: theme.colors.border,
    maxWidth: '100%',
  },
  thinkingLabel: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
    fontWeight: theme.font.weightSemibold,
    marginBottom: 4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  thinkingText: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
    fontStyle: 'italic',
    lineHeight: 18,
  },
  toolEvents: {
    gap: 4,
    marginBottom: 4,
  },
  toolPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.full,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: theme.colors.border,
    gap: 6,
  },
  toolPillRunning: {
    borderColor: theme.colors.accent,
    backgroundColor: theme.colors.accentGlow,
  },
  toolIcon: {
    fontSize: 14,
  },
  toolLabel: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
  },
  toolDone: {
    fontSize: 12,
    color: theme.colors.success,
    fontWeight: theme.font.weightBold,
  },
});
