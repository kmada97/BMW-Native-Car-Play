package com.kalyan.bmwdashboardprobe;

/** Single-frame scheduling policy; monotonic milliseconds, no Android dependency. */
public final class FrameSchedule {
    public static final long NEVER=Long.MAX_VALUE;
    public static final long INTERACTION_MS=5000; // AAIdrive USB quality policy
    public static final int INTERACTION_QUALITY=40, SETTLED_QUALITY=65;
    private long revision=1, sentRevision, interactiveUntil=-1, lastFrameStart=-1;
    private int sentQuality;
    public void invalidate() { revision++; }
    public void input(long nowMs) { invalidate();interactiveUntil=Math.max(interactiveUntil,nowMs+INTERACTION_MS); }
    public int quality(long nowMs) { return nowMs<interactiveUntil?INTERACTION_QUALITY:SETTLED_QUALITY; }
    public long revision() { return revision; }
    public void sent(long frameStartMs,long frameRevision,int quality) {
        lastFrameStart=frameStartMs;sentRevision=frameRevision;sentQuality=quality;
    }
    /** Dirty input bypasses animation pacing; queued input must run before another image RPC. */
    public long delay(long nowMs,int animationFps,boolean inputPending) {
        if(inputPending)return 16;
        if(revision!=sentRevision)return 0;
        long delay=NEVER;
        if(sentQuality==INTERACTION_QUALITY)delay=Math.max(0,interactiveUntil-nowMs);
        if(animationFps>0)delay=Math.min(delay,Math.max(0,lastFrameStart+1000/animationFps-nowMs));
        return delay;
    }
}
