import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  SafeAreaView,
  Keyboard,
} from 'react-native';
import { theme } from '../theme';
import { MessageBubble, MessageData, ToolEvent } from '../components/MessageBubble';
import { QuickActions } from '../components/QuickActions';
import { assistantAPI, ChatMessage, StreamEvent } from '../services/api';

let messageIdCounter = 0;
const nextId = () => `msg_${++messageIdCounter}`;

export function ChatScreen() {
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const flatListRef = useRef<FlatList>(null);
  const chatHistoryRef = useRef<ChatMessage[]>([]);

  useEffect(() => {
    assistantAPI.connect();
    return () => assistantAPI.disconnect();
  }, []);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 50);
  }, []);

  const sendMessage = useCallback((text: string) => {
    if (!text.trim() || isStreaming) return;

    const userText = text.trim();
    setInputText('');
    setShowQuickActions(false);
    Keyboard.dismiss();

    // Add user message to UI
    const userMsg: MessageData = {
      id: nextId(),
      role: 'user',
      content: userText,
      status: 'done',
    };

    // Add placeholder AI message
    const aiMsgId = nextId();
    const aiMsg: MessageData = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      status: 'sending',
      toolEvents: [],
    };

    setMessages(prev => [...prev, userMsg, aiMsg]);
    scrollToBottom();

    // Update conversation history
    chatHistoryRef.current.push({ role: 'user', content: userText });

    setIsStreaming(true);
    let aiText = '';
    let aiThinking = '';
    let currentToolEvents: ToolEvent[] = [];

    assistantAPI.sendMessage(chatHistoryRef.current, (event: StreamEvent) => {
      setMessages(prev => {
        const idx = prev.findIndex(m => m.id === aiMsgId);
        if (idx === -1) return prev;
        const updated = [...prev];
        const msg = { ...updated[idx] };

        switch (event.type) {
          case 'thinking_delta':
            aiThinking += event.thinking;
            msg.thinking = aiThinking;
            msg.status = 'streaming';
            break;

          case 'text_delta':
            aiText += event.text;
            msg.content = aiText;
            msg.status = 'streaming';
            break;

          case 'tool_start':
          case 'tool_executing': {
            const existing = currentToolEvents.findIndex(
              t => t.tool_name === event.tool_name && t.status === 'running'
            );
            if (existing === -1) {
              currentToolEvents = [
                ...currentToolEvents,
                { tool_name: event.tool_name, status: 'running' },
              ];
            }
            msg.toolEvents = [...currentToolEvents];
            break;
          }

          case 'tool_result': {
            currentToolEvents = currentToolEvents.map(t =>
              t.tool_name === event.tool_name && t.status === 'running'
                ? { ...t, status: 'done', result: event.result }
                : t
            );
            msg.toolEvents = [...currentToolEvents];
            break;
          }

          case 'done':
            msg.status = 'done';
            setIsStreaming(false);
            chatHistoryRef.current.push({ role: 'assistant', content: aiText });
            scrollToBottom();
            break;

          case 'error':
            msg.content = `Error: ${event.message}`;
            msg.status = 'error';
            setIsStreaming(false);
            break;
        }

        updated[idx] = msg;
        return updated;
      });

      scrollToBottom();
    });
  }, [isStreaming, scrollToBottom]);

  const clearChat = useCallback(() => {
    setMessages([]);
    chatHistoryRef.current = [];
    setShowQuickActions(true);
    setIsStreaming(false);
  }, []);

  const renderMessage = useCallback(({ item }: { item: MessageData }) => (
    <MessageBubble message={item} />
  ), []);

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View style={styles.statusDot} />
            <Text style={styles.headerTitle}>AI Assistant</Text>
          </View>
          <TouchableOpacity onPress={clearChat} style={styles.clearBtn}>
            <Text style={styles.clearBtnText}>New Chat</Text>
          </TouchableOpacity>
        </View>

        {/* Message list */}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={item => item.id}
          renderItem={renderMessage}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={scrollToBottom}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={<WelcomeScreen />}
          ListFooterComponent={<View style={{ height: 8 }} />}
        />

        {/* Quick actions (shown when empty) */}
        {showQuickActions && messages.length === 0 && (
          <QuickActions onSelect={sendMessage} />
        )}

        {/* Input area */}
        <View style={styles.inputContainer}>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              value={inputText}
              onChangeText={setInputText}
              placeholder="Ask me anything..."
              placeholderTextColor={theme.colors.textMuted}
              multiline
              maxLength={4000}
              returnKeyType="default"
              editable={!isStreaming}
            />
            <TouchableOpacity
              style={[
                styles.sendButton,
                (!inputText.trim() || isStreaming) && styles.sendButtonDisabled,
              ]}
              onPress={() => sendMessage(inputText)}
              disabled={!inputText.trim() || isStreaming}
              activeOpacity={0.8}
            >
              {isStreaming ? (
                <ActivityIndicator size="small" color={theme.colors.textOnPrimary} />
              ) : (
                <Text style={styles.sendIcon}>↑</Text>
              )}
            </TouchableOpacity>
          </View>
          <Text style={styles.disclaimer}>
            Can search, trade stocks & crypto, and send payments
          </Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function WelcomeScreen() {
  return (
    <View style={styles.welcome}>
      <Text style={styles.welcomeIcon}>✦</Text>
      <Text style={styles.welcomeTitle}>Your AI Assistant</Text>
      <Text style={styles.welcomeSubtitle}>
        Powered by Claude Opus — I can search the web, trade stocks & crypto, make payments, and do anything online.
      </Text>
      <View style={styles.capabilities}>
        {[
          { icon: '🔍', text: 'Search anything online' },
          { icon: '📈', text: 'Trade stocks with Alpaca' },
          { icon: '₿', text: 'Buy & sell crypto on Coinbase' },
          { icon: '💳', text: 'Send payments via Stripe' },
          { icon: '🌐', text: 'Browse and fetch any webpage' },
        ].map((cap, i) => (
          <View key={i} style={styles.capability}>
            <Text style={styles.capabilityIcon}>{cap.icon}</Text>
            <Text style={styles.capabilityText}>{cap.text}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    backgroundColor: theme.colors.background,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.success,
  },
  headerTitle: {
    fontSize: theme.font.sizeLg,
    fontWeight: theme.font.weightBold,
    color: theme.colors.textPrimary,
    letterSpacing: -0.3,
  },
  clearBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: theme.radius.full,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  clearBtnText: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
    fontWeight: theme.font.weightMedium,
  },
  messageList: {
    paddingTop: 16,
    flexGrow: 1,
  },
  inputContainer: {
    padding: 12,
    paddingBottom: Platform.OS === 'ios' ? 4 : 12,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
    backgroundColor: theme.colors.background,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 10,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.xl,
    paddingHorizontal: 18,
    paddingVertical: 12,
    paddingRight: 52,
    fontSize: theme.font.sizeMd,
    color: theme.colors.textPrimary,
    borderWidth: 1,
    borderColor: theme.colors.border,
    lineHeight: 20,
  },
  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: theme.colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
  },
  sendButtonDisabled: {
    backgroundColor: theme.colors.border,
    shadowOpacity: 0,
    elevation: 0,
  },
  sendIcon: {
    fontSize: 18,
    color: '#FFFFFF',
    fontWeight: theme.font.weightBold,
    marginTop: -1,
  },
  disclaimer: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
    textAlign: 'center',
    marginTop: 8,
  },
  welcome: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    paddingTop: 48,
  },
  welcomeIcon: {
    fontSize: 48,
    color: theme.colors.primary,
    marginBottom: 16,
  },
  welcomeTitle: {
    fontSize: theme.font.sizeXxl,
    fontWeight: theme.font.weightBold,
    color: theme.colors.textPrimary,
    marginBottom: 12,
    textAlign: 'center',
  },
  welcomeSubtitle: {
    fontSize: theme.font.sizeMd,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 32,
  },
  capabilities: {
    gap: 12,
    alignSelf: 'stretch',
  },
  capability: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  capabilityIcon: {
    fontSize: 20,
  },
  capabilityText: {
    fontSize: theme.font.sizeMd,
    color: theme.colors.textSecondary,
    fontWeight: theme.font.weightMedium,
  },
});
