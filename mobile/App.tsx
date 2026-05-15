import { CameraView, useCameraPermissions } from "expo-camera";
import { Image } from "expo-image";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { ConnectionBar } from "./src/components/ConnectionBar";
import { DEFAULT_BACKEND_HOST } from "./src/config";
import { useHudStream } from "./src/hooks/useHudStream";

function HudScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraReady, setCameraReady] = useState(false);
  const {
    cameraRef,
    serverHost,
    setServerHost,
    connectionState,
    statusMessage,
    hudUri,
    isStreaming,
    framesSent,
    captureFps,
    connect,
    disconnect,
    startStreaming,
    stopStreaming,
  } = useHudStream(cameraReady);

  useEffect(() => {
    setServerHost(DEFAULT_BACKEND_HOST);
  }, [setServerHost]);

  if (!permission) {
    return (
      <View style={styles.center}>
        <Text style={styles.muted}>Requesting camera permission…</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.text}>Camera access is required for SkulVision.</Text>
        <Text style={styles.link} onPress={() => void requestPermission()}>
          Grant permission
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <StatusBar style="light" hidden={isStreaming} />

      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        facing="back"
        onCameraReady={() => setCameraReady(true)}
      />

      {hudUri ? (
        <Image
          source={{ uri: hudUri }}
          style={StyleSheet.absoluteFill}
          contentFit="cover"
          transition={0}
          cachePolicy="none"
        />
      ) : null}

      {/* Top-left Menu — stays above keyboard */}
      <ConnectionBar
        serverHost={serverHost}
        onChangeHost={setServerHost}
        connectionState={connectionState}
        statusMessage={statusMessage}
        isStreaming={isStreaming}
        framesSent={framesSent}
        captureFps={captureFps}
        onConnect={() => void connect(serverHost)}
        onDisconnect={disconnect}
        onStart={startStreaming}
        onStop={stopStreaming}
      />
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <HudScreen />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#000",
  },
  center: {
    flex: 1,
    backgroundColor: "#0a0a0a",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 16,
  },
  text: { color: "#fff", textAlign: "center", fontSize: 16 },
  muted: { color: "#888" },
  link: { color: "#00ffff", fontWeight: "700", fontSize: 16 },
});
