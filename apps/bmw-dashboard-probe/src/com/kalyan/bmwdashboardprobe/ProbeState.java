package com.kalyan.bmwdashboardprobe;

/** Pure state, shared by the Pi preview and the BMW image stream. */
public final class ProbeState {
    public int selected = 0;
    public boolean detail;
    public int inputs;
    public long inputReceivedNs;
    public int fpsLimit = 0; // Static dashboard: send only changes, optional animation diagnostic.
    public static final long SESSION_MS = 15 * 60 * 1000;
    public void rotate(int direction, long nowNs) {
        selected = Math.floorMod(selected + Integer.signum(direction), 4);
        inputs++;
        inputReceivedNs = nowNs;
    }
    public void click(long nowNs) {
        inputs++;
        inputReceivedNs = nowNs;
        if (selected == 3) {
            fpsLimit = fpsLimit == 0 ? 2 : fpsLimit == 2 ? 5 : fpsLimit == 5 ? 8 : fpsLimit == 8 ? 12 : 0;
        } else detail = !detail;
    }
}
