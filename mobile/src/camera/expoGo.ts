import Constants from "expo-constants";

/** True when running inside Expo Go (no custom native modules). */
export function isExpoGo(): boolean {
  return Constants.appOwnership === "expo";
}
