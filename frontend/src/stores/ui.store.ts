import { create } from "zustand";

type ThemeMode = "dark" | "midnight";

interface UIStore {
  theme: ThemeMode;
  drawerOpen: boolean;
  dialogs: Record<string, boolean>;
  notifications: string[];
  setTheme: (theme: ThemeMode) => void;
  setDrawerOpen: (open: boolean) => void;
  setDialog: (key: string, open: boolean) => void;
  pushNotification: (message: string) => void;
  popNotification: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  theme: "dark",
  drawerOpen: false,
  dialogs: {},
  notifications: [],
  setTheme: (theme) => set({ theme }),
  setDrawerOpen: (drawerOpen) => set({ drawerOpen }),
  setDialog: (key, open) => set((state) => ({ dialogs: { ...state.dialogs, [key]: open } })),
  pushNotification: (message) => set((state) => ({ notifications: [...state.notifications, message] })),
  popNotification: () => set((state) => ({ notifications: state.notifications.slice(1) })),
}));
