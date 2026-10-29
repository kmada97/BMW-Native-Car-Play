package com.kalyan.bmwstartup;

/** Pure state machine: five starts per attachment, then quiet until detach. */
public final class RetryPolicy {
    public static final int MAX_ATTEMPTS = 5;
    public static final long INTERVAL_MS = 10_000L;
    private boolean attached;
    private int attempts;
    private long nextAttempt;

    public boolean shouldStart(boolean bmwAttached, long monotonicMillis) {
        if (!bmwAttached) {
            detached();
            return false;
        }
        if (!attached) {
            attached = true;
            attempts = 0;
            nextAttempt = monotonicMillis;
        }
        if (attempts >= MAX_ATTEMPTS || monotonicMillis < nextAttempt) return false;
        attempts++;
        nextAttempt = monotonicMillis + INTERVAL_MS;
        return true;
    }

    public void detached() { attached = false; attempts = 0; nextAttempt = 0; }
    public int attempts() { return attempts; }
}
