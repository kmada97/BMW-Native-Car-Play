package com.kalyan.bmwstartup;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.ArrayList;

public final class MainActivity extends Activity {
    private TextView status;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(40, 40, 40, 40);
        TextView title = new TextView(this);
        title.setText("BMW Startup Helper");
        title.setTextSize(26);
        layout.addView(title);
        TextView description = new TextView(this);
        description.setText("Starts AAIdrive when the BMW USB connection is present. "
                + "Runs after reboot. Does not change sound, pairing, or the BMW app.");
        layout.addView(description);
        Button enable = new Button(this);
        enable.setText("Enable startup helper");
        enable.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { enable(); }
        });
        layout.addView(enable);
        Button disable = new Button(this);
        disable.setText("Disable startup helper");
        disable.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                StartupService.setEnabled(MainActivity.this, false);
                stopService(new Intent(MainActivity.this, StartupService.class));
                refresh();
            }
        });
        layout.addView(disable);
        status = new TextView(this);
        layout.addView(status);
        setContentView(layout);
        refresh();
        // Explicit local setup convenience; merely opening the app does not enable it.
        if (getIntent().getBooleanExtra("enable", false)) enable();
    }
    private void enable() {
        ArrayList<String> missing = new ArrayList<>();
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) missing.add(Manifest.permission.BLUETOOTH_CONNECT);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) missing.add(Manifest.permission.POST_NOTIFICATIONS);
        if (!missing.isEmpty()) { requestPermissions(missing.toArray(new String[0]), 1); return; }
        StartupService.setEnabled(this, true);
        try {
            startForegroundService(new Intent(this, StartupService.class));
            refresh();
        } catch (RuntimeException e) {
            StartupService.setEnabled(this, false);
            status.setText("Could not start: " + e.getClass().getSimpleName());
        }
    }
    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(request, permissions, grants);
        for (int grant : grants) {
            if (grant != PackageManager.PERMISSION_GRANTED) {
                status.setText("Permission was not granted. Helper remains disabled.");
                return;
            }
        }
        if (grants.length > 0) enable();
    }
    private void refresh() {
        status.setText(StartupService.isEnabled(this) ? "Enabled. You may return to the Home screen."
                : "Disabled.");
    }
}
