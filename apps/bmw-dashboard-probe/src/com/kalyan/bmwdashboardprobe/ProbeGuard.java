package com.kalyan.bmwdashboardprobe;

import java.io.InterruptedIOException;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

/** Independent cancellation; it never queues a stop behind the RPC that must be stopped. */
public final class ProbeGuard {
    private final ScheduledExecutorService timers;
    private final Consumer<String> onCancel;
    private final AtomicBoolean cancelled=new AtomicBoolean();
    private final ScheduledFuture<?> deadline;
    public ProbeGuard(ScheduledExecutorService timers,long sessionMs,Consumer<String> onCancel) {
        this.timers=timers;this.onCancel=onCancel;
        deadline=timers.schedule(()->cancel("session_deadline"),sessionMs,TimeUnit.MILLISECONDS);
    }
    public boolean isCancelled(){return cancelled.get();}
    public void cancel(String reason) {
        if(cancelled.compareAndSet(false,true)) {
            deadline.cancel(false);
            timers.execute(()->onCancel.accept(reason));
        }
    }
    public <T> T call(String name,long timeoutMs,Callable<T> call) throws Exception {
        if(isCancelled())throw new InterruptedIOException("Probe cancelled");
        ScheduledFuture<?> timeout=timers.schedule(()->cancel("rpc_timeout:"+name),timeoutMs,TimeUnit.MILLISECONDS);
        try {
            T result=call.call();
            if(isCancelled())throw new InterruptedIOException("Probe cancelled");
            return result;
        } finally {timeout.cancel(false);}
    }
}
