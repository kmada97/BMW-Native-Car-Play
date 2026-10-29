package com.kalyan.bmwstartup;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.hardware.usb.UsbAccessory;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;

public final class StartupService extends Service {
    public static final String TAG = "BMWStartupHelper";
    private static final String CHANNEL = "bmw_startup";
    private static final String ACTION_STOP = "com.kalyan.bmwstartup.STOP";
    private static final String AAIDRIVE = "me.hufman.androidautoidrive";
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final RetryPolicy retry = new RetryPolicy();
    private String displayedStatus = "";
    private boolean receiverRegistered;

    static boolean isEnabled(Context c) {
        return c.getSharedPreferences("startup", MODE_PRIVATE).getBoolean("enabled", false);
    }
    static void setEnabled(Context c, boolean enabled) {
        c.getSharedPreferences("startup", MODE_PRIVATE).edit().putBoolean("enabled", enabled).apply();
    }

    private final BroadcastReceiver detachReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            // This protected platform broadcast catches fast disconnect/reconnect between polls.
            if (UsbManager.ACTION_USB_ACCESSORY_DETACHED.equals(intent.getAction())) {
                retry.detached();
                handler.removeCallbacks(poll);
                handler.postDelayed(poll, 1_000L);
                Log.i(TAG, "USB detached; next BMW attachment may start AAIdrive");
            }
        }
    };

    private final Runnable poll = new Runnable() {
        @Override public void run() {
            if (!isEnabled(StartupService.this)) { stopSelf(); return; }
            try {
                boolean bmw = bmwAccessoryPresent();
                if (retry.shouldStart(bmw, SystemClock.elapsedRealtime())) {
                    Intent start = new Intent(AAIDRIVE + ".CarConnectionListener_START")
                            .setComponent(new ComponentName(AAIDRIVE, AAIDRIVE + ".CarConnectionListener"));
                    sendBroadcast(start);
                    Log.i(TAG, "BMW accessory: sent normal AAIdrive start request " + retry.attempts()
                            + "/" + RetryPolicy.MAX_ATTEMPTS);
                }
                String text = !bmw ? "Waiting for BMW USB"
                        : retry.attempts() < RetryPolicy.MAX_ATTEMPTS ? "Starting AAIdrive for BMW"
                        : "BMW USB present; start requests complete";
                updateStatus(text);
            } catch (RuntimeException e) {
                Log.e(TAG, "USB/start check failed", e);
                updateStatus("Connection check needs attention");
            }
            handler.postDelayed(this, RetryPolicy.INTERVAL_MS);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        getSystemService(NotificationManager.class).createNotificationChannel(
                new NotificationChannel(CHANNEL, "BMW startup", NotificationManager.IMPORTANCE_LOW));
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            setEnabled(this, false);
            stopSelf();
            return START_NOT_STICKY;
        }
        if (!isEnabled(this)) { stopSelf(); return START_NOT_STICKY; }
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) {
            Log.e(TAG, "Missing connected-device foreground-service prerequisite permission");
            stopSelf();
            return START_NOT_STICKY;
        }
        Notification notification = notification("Waiting for BMW USB");
        if (Build.VERSION.SDK_INT >= 29) startForeground(1, notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        else startForeground(1, notification);
        if (!receiverRegistered) {
            IntentFilter filter = new IntentFilter(UsbManager.ACTION_USB_ACCESSORY_DETACHED);
            if (Build.VERSION.SDK_INT >= 33) registerReceiver(detachReceiver, filter, RECEIVER_EXPORTED);
            else registerReceiver(detachReceiver, filter);
            receiverRegistered = true;
        }
        handler.removeCallbacks(poll);
        handler.post(poll);
        Log.i(TAG, "USB watcher active");
        return START_STICKY;
    }

    private boolean bmwAccessoryPresent() {
        UsbManager usb = getSystemService(UsbManager.class);
        UsbAccessory[] accessories = usb == null ? null : usb.getAccessoryList();
        if (accessories == null) return false;
        for (UsbAccessory accessory : accessories) {
            if ("BMW Group".equals(accessory.getManufacturer()) && "BMW".equals(accessory.getModel()))
                return true;
        }
        return false;
    }

    private Notification notification(String text) {
        PendingIntent open = PendingIntent.getActivity(this, 1, new Intent(this, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent stop = PendingIntent.getService(this, 2,
                new Intent(this, StartupService.class).setAction(ACTION_STOP),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_menu_manage)
                .setContentTitle("BMW Startup Helper").setContentText(text)
                .setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
                .addAction(new Notification.Action.Builder(null, "Disable", stop).build()).build();
    }
    private void updateStatus(String text) {
        if (!text.equals(displayedStatus)) {
            displayedStatus = text;
            getSystemService(NotificationManager.class).notify(1, notification(text));
            Log.i(TAG, text);
        }
    }
    @Override public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (receiverRegistered) unregisterReceiver(detachReceiver);
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
