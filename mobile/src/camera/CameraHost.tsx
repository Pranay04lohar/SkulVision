import { forwardRef } from "react";
import { StyleSheet, Text, View } from "react-native";

import { isExpoGo } from "./expoGo";
import { ExpoHudCamera } from "./ExpoHudCamera";
import type { HudCameraHandle } from "./types";
import { VisionHudCamera } from "./VisionHudCamera";

type Props = {
  isActive: boolean;
  onReady: () => void;
};

export const CameraHost = forwardRef<HudCameraHandle, Props>(function CameraHost(
  props,
  ref
) {
  if (isExpoGo()) {
    return (
      <View style={styles.wrap}>
        <ExpoHudCamera ref={ref} {...props} />
        <View style={styles.banner} pointerEvents="none">
          <Text style={styles.bannerText}>
            Expo Go: ~3–5 FPS. For video HUD (~12 FPS): npx expo run:android
          </Text>
        </View>
      </View>
    );
  }

  return <VisionHudCamera ref={ref} {...props} />;
});

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  banner: {
    position: "absolute",
    bottom: 120,
    left: 12,
    right: 12,
    backgroundColor: "rgba(0,0,0,0.75)",
    padding: 10,
    borderRadius: 8,
  },
  bannerText: { color: "#ffcc00", fontSize: 12, textAlign: "center" },
});
