import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ConnectionState } from "../services/skulVisionSocket";

type Props = {
  serverHost: string;
  onChangeHost: (host: string) => void;
  connectionState: ConnectionState;
  statusMessage: string;
  isStreaming: boolean;
  framesSent: number;
  captureFps: number;
  onConnect: () => void;
  onDisconnect: () => void;
  onStart: () => void;
  onStop: () => void;
};

const STATE_COLOR: Record<ConnectionState, string> = {
  idle: "#666",
  connecting: "#f5a623",
  connected: "#00ffff",
  error: "#ff4444",
};

export function ConnectionBar({
  serverHost,
  onChangeHost,
  connectionState,
  statusMessage,
  isStreaming,
  framesSent,
  captureFps,
  onConnect,
  onDisconnect,
  onStart,
  onStop,
}: Props) {
  const insets = useSafeAreaInsets();
  const connected = connectionState === "connected";
  const connecting = connectionState === "connecting";
  const dotColor = STATE_COLOR[connectionState];

  const [menuOpen, setMenuOpen] = useState(true);

  useEffect(() => {
    if (isStreaming) {
      const t = setTimeout(() => setMenuOpen(false), 1500);
      return () => clearTimeout(t);
    } else {
      setMenuOpen(true);
    }
  }, [isStreaming]);

  const pillLabel = isStreaming
    ? `HUD · ${captureFps.toFixed(0)} fps · ${framesSent} sent`
    : menuOpen
      ? "Menu ▲"
      : "Menu ▼";

  return (
    <KeyboardAvoidingView
      style={[styles.anchor, { top: insets.top + 8, left: 12 }]}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={insets.top + 8}
    >
      {/* Menu pill — fixed top-left like mockup */}
      <Pressable
        style={styles.menuPill}
        onPress={() => setMenuOpen((o) => !o)}
      >
        <View style={[styles.dot, { backgroundColor: dotColor }]} />
        <Text style={styles.menuText}>{pillLabel}</Text>
      </Pressable>

      {menuOpen && (
        <ScrollView
          style={styles.panelScroll}
          keyboardShouldPersistTaps="handled"
          bounces={false}
        >
          <View style={styles.panel}>
            <Text style={styles.label}>Server IP</Text>
            <TextInput
              style={styles.input}
              value={serverHost}
              onChangeText={onChangeHost}
              placeholder="192.168.0.106"
              placeholderTextColor="#999"
              autoCapitalize="none"
              autoCorrect={false}
              editable={!connected && !connecting}
              keyboardType="decimal-pad"
              returnKeyType="done"
              onSubmitEditing={() => Keyboard.dismiss()}
            />

            <View style={styles.row}>
              {!connected ? (
                <Pressable
                  style={[
                    styles.btn,
                    styles.btnDark,
                    connecting && styles.btnDisabled,
                  ]}
                  onPress={onConnect}
                  disabled={connecting || !serverHost.trim()}
                >
                  {connecting ? (
                    <ActivityIndicator color="#fff" size="small" />
                  ) : (
                    <Text style={styles.btnTextLight}>Connect</Text>
                  )}
                </Pressable>
              ) : (
                <>
                  {!isStreaming ? (
                    <Pressable style={[styles.btn, styles.btnDark]} onPress={onStart}>
                      <Text style={styles.btnTextLight}>Start HUD</Text>
                    </Pressable>
                  ) : (
                    <Pressable style={[styles.btn, styles.btnWarn]} onPress={onStop}>
                      <Text style={styles.btnTextLight}>Stop</Text>
                    </Pressable>
                  )}
                  <Pressable style={[styles.btn, styles.btnOutline]} onPress={onDisconnect}>
                    <Text style={styles.btnTextDark}>Disconnect</Text>
                  </Pressable>
                </>
              )}
            </View>

            {!!statusMessage && (
              <Text style={styles.error} numberOfLines={3}>
                {statusMessage}
              </Text>
            )}
          </View>
        </ScrollView>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  anchor: {
    position: "absolute",
    zIndex: 100,
    maxWidth: 280,
    alignItems: "flex-start",
  },
  menuPill: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.96)",
    borderRadius: 28,
    paddingHorizontal: 18,
    paddingVertical: 11,
    gap: 8,
    borderWidth: 2,
    borderColor: "#111",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.35,
    shadowRadius: 4,
    elevation: 6,
  },
  menuText: {
    color: "#111",
    fontSize: 16,
    fontWeight: "700",
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  panelScroll: {
    maxHeight: 320,
    marginTop: 8,
  },
  panel: {
    backgroundColor: "rgba(255,255,255,0.96)",
    borderRadius: 14,
    padding: 14,
    gap: 10,
    borderWidth: 2,
    borderColor: "#111",
    width: 260,
  },
  label: {
    color: "#444",
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.6,
  },
  input: {
    backgroundColor: "#f2f2f2",
    color: "#111",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    borderWidth: 1,
    borderColor: "#ccc",
  },
  row: {
    flexDirection: "row",
    gap: 8,
  },
  btn: {
    flex: 1,
    paddingVertical: 11,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 42,
  },
  btnDark: {
    backgroundColor: "#111",
  },
  btnWarn: {
    backgroundColor: "#e53935",
  },
  btnOutline: {
    backgroundColor: "#fff",
    borderWidth: 1.5,
    borderColor: "#111",
  },
  btnDisabled: { opacity: 0.5 },
  btnTextLight: { color: "#fff", fontWeight: "700", fontSize: 14 },
  btnTextDark: { color: "#111", fontWeight: "700", fontSize: 14 },
  error: { color: "#c62828", fontSize: 12, lineHeight: 17 },
});
