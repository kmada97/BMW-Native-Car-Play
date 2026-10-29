package com.kalyan.bmwstartup;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public final class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)) return;
        if (!StartupService.isEnabled(context)) return;
        try {
            context.startForegroundService(new Intent(context, StartupService.class));
        } catch (RuntimeException e) {
            Log.e(StartupService.TAG, "Boot service start failed", e);
        }
    }
}
