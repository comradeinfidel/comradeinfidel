import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Switch,
  SafeAreaView,
  Alert,
} from 'react-native';
import { theme } from '../theme';

type SettingRow = {
  label: string;
  value: string;
  placeholder: string;
  secure?: boolean;
  hint?: string;
};

const API_SETTINGS: SettingRow[] = [
  {
    label: 'Backend URL',
    value: 'http://localhost:8000',
    placeholder: 'http://your-server.com:8000',
    hint: 'URL of your AI assistant backend',
  },
];

const INTEGRATION_SETTINGS = [
  {
    section: '📈 Alpaca (Stocks)',
    items: [
      { label: 'API Key', placeholder: 'Your Alpaca API key', secure: true },
      { label: 'Secret Key', placeholder: 'Your Alpaca secret key', secure: true },
    ],
    docsUrl: 'https://alpaca.markets',
    note: 'Paper trading enabled by default. Go live by updating ALPACA_BASE_URL in backend .env',
  },
  {
    section: '₿ Coinbase (Crypto)',
    items: [
      { label: 'API Key', placeholder: 'organizations/.../apiKeys/...', secure: false },
      { label: 'API Secret', placeholder: '-----BEGIN EC PRIVATE KEY-----\n...', secure: true },
    ],
    docsUrl: 'https://docs.cdp.coinbase.com/advanced-trade/docs/rest-api-auth',
    note: 'Create a Coinbase Advanced Trade API key with trading permissions',
  },
  {
    section: '💳 Stripe (Payments)',
    items: [
      { label: 'Secret Key', placeholder: 'sk_test_...', secure: true },
    ],
    docsUrl: 'https://stripe.com/docs/keys',
    note: 'Use test keys (sk_test_...) while developing',
  },
];

function SettingSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );
}

function InputRow({
  label,
  placeholder,
  secure,
  hint,
}: {
  label: string;
  placeholder: string;
  secure?: boolean;
  hint?: string;
}) {
  const [value, setValue] = useState('');
  const [show, setShow] = useState(false);

  return (
    <View style={styles.inputRow}>
      <Text style={styles.inputLabel}>{label}</Text>
      <View style={styles.inputWrapper}>
        <TextInput
          style={styles.input}
          value={value}
          onChangeText={setValue}
          placeholder={placeholder}
          placeholderTextColor={theme.colors.textMuted}
          secureTextEntry={secure && !show}
          autoCapitalize="none"
          autoCorrect={false}
        />
        {secure && (
          <TouchableOpacity
            style={styles.toggleBtn}
            onPress={() => setShow(s => !s)}
          >
            <Text style={styles.toggleText}>{show ? '🙈' : '👁️'}</Text>
          </TouchableOpacity>
        )}
      </View>
      {hint && <Text style={styles.hint}>{hint}</Text>}
    </View>
  );
}

export function SettingsScreen() {
  const [paperTrading, setPaperTrading] = useState(true);

  const showInfo = () => {
    Alert.alert(
      'About API Keys',
      'API keys are configured in the backend .env file. This screen is for reference. Edit backend/.env to set your actual keys.',
      [{ text: 'OK' }]
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Settings</Text>
          <TouchableOpacity onPress={showInfo}>
            <Text style={styles.infoBtn}>ℹ️</Text>
          </TouchableOpacity>
        </View>

        {/* Status */}
        <View style={styles.statusCard}>
          <View style={styles.statusRow}>
            <View style={styles.statusDot} />
            <Text style={styles.statusText}>Backend Connected</Text>
          </View>
          <Text style={styles.modelText}>Model: Claude Opus 4.6</Text>
        </View>

        <SettingSection title="🔌 Backend">
          <InputRow
            label="Backend URL"
            placeholder="http://localhost:8000"
            hint="URL of your AI assistant backend server"
          />
          <View style={styles.switchRow}>
            <View>
              <Text style={styles.switchLabel}>Paper Trading (Alpaca)</Text>
              <Text style={styles.switchHint}>
                {paperTrading ? 'Using paper trading (safe for testing)' : '⚠️ Live trading enabled'}
              </Text>
            </View>
            <Switch
              value={paperTrading}
              onValueChange={setPaperTrading}
              trackColor={{ false: theme.colors.danger + '60', true: theme.colors.success + '60' }}
              thumbColor={paperTrading ? theme.colors.success : theme.colors.danger}
            />
          </View>
        </SettingSection>

        {INTEGRATION_SETTINGS.map((integration) => (
          <SettingSection key={integration.section} title={integration.section}>
            {integration.items.map((item) => (
              <InputRow
                key={item.label}
                label={item.label}
                placeholder={item.placeholder}
                secure={item.secure}
              />
            ))}
            <View style={styles.noteBox}>
              <Text style={styles.noteText}>{integration.note}</Text>
              <Text style={styles.noteLink}>Docs: {integration.docsUrl}</Text>
            </View>
          </SettingSection>
        ))}

        <SettingSection title="🛡️ Safety">
          <View style={styles.safetyItem}>
            <Text style={styles.safetyIcon}>✅</Text>
            <View style={styles.safetyText}>
              <Text style={styles.safetyLabel}>Confirm before trading</Text>
              <Text style={styles.safetyHint}>AI will always confirm trades over $100</Text>
            </View>
          </View>
          <View style={styles.safetyItem}>
            <Text style={styles.safetyIcon}>✅</Text>
            <View style={styles.safetyText}>
              <Text style={styles.safetyLabel}>Payment confirmation</Text>
              <Text style={styles.safetyHint}>All payments require explicit approval</Text>
            </View>
          </View>
          <View style={styles.safetyItem}>
            <Text style={styles.safetyIcon}>✅</Text>
            <View style={styles.safetyText}>
              <Text style={styles.safetyLabel}>Adaptive AI thinking</Text>
              <Text style={styles.safetyHint}>Claude reasons deeply before acting</Text>
            </View>
          </View>
        </SettingSection>

        <View style={styles.footer}>
          <Text style={styles.footerText}>AI Personal Assistant v1.0</Text>
          <Text style={styles.footerSub}>Powered by Claude Opus 4.6</Text>
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  infoBtn: {
    fontSize: 22,
  },
  statusCard: {
    margin: 16,
    backgroundColor: theme.colors.successGlow,
    borderRadius: theme.radius.lg,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.success + '30',
    gap: 4,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.success,
  },
  statusText: {
    fontSize: theme.font.sizeMd,
    color: theme.colors.success,
    fontWeight: theme.font.weightSemibold,
  },
  modelText: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
  },
  section: {
    marginHorizontal: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: theme.font.sizeMd,
    fontWeight: theme.font.weightBold,
    color: theme.colors.textPrimary,
    marginBottom: 10,
    marginLeft: 4,
  },
  sectionContent: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    overflow: 'hidden',
  },
  inputRow: {
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    gap: 6,
  },
  inputLabel: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
    fontWeight: theme.font.weightMedium,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderRadius: theme.radius.sm,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  input: {
    flex: 1,
    padding: 10,
    fontSize: theme.font.sizeSm,
    color: theme.colors.textPrimary,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  toggleBtn: {
    padding: 10,
  },
  toggleText: {
    fontSize: 16,
  },
  hint: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
    lineHeight: 16,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  switchLabel: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
    fontWeight: theme.font.weightMedium,
  },
  switchHint: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
    marginTop: 2,
  },
  noteBox: {
    padding: 12,
    backgroundColor: theme.colors.primaryGlow,
    borderRadius: theme.radius.sm,
    margin: 12,
    gap: 4,
  },
  noteText: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.primaryLight,
    lineHeight: 16,
  },
  noteLink: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.accent,
  },
  safetyItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 14,
    gap: 12,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  safetyIcon: {
    fontSize: 16,
    marginTop: 1,
  },
  safetyText: {
    flex: 1,
    gap: 2,
  },
  safetyLabel: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textPrimary,
    fontWeight: theme.font.weightMedium,
  },
  safetyHint: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
  },
  footer: {
    alignItems: 'center',
    padding: 24,
    gap: 4,
  },
  footerText: {
    fontSize: theme.font.sizeSm,
    color: theme.colors.textSecondary,
    fontWeight: theme.font.weightMedium,
  },
  footerSub: {
    fontSize: theme.font.sizeXs,
    color: theme.colors.textMuted,
  },
});

// Need Platform for styles
import { Platform } from 'react-native';
