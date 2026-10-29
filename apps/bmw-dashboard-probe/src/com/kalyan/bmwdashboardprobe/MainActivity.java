package com.kalyan.bmwdashboardprobe;

import android.app.Activity;
import android.content.*;
import android.graphics.Canvas;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Log;
import android.view.*;
import android.widget.*;

public final class MainActivity extends Activity {
    private TextView status;
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        Log.i(DashboardService.TAG,"Activity create build="+BuildIdentity.VERSION+" source="+BuildIdentity.SOURCE_SHA256);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(20,16,20,16);
        status=new TextView(this);status.setTextSize(19);root.addView(status);
        TextView notice=new TextView(this);notice.setText("Parked display/input test only. Navigation and calls are demo panels. No CarPlay receiver is included. Frame RPC timing is not physical display latency.");root.addView(notice);
        LinearLayout actions=new LinearLayout(this);
        Button arm=new Button(this);arm.setText("Arm next connection (15 min)");arm.setOnClickListener(v->arm());actions.addView(arm);
        Button stop=new Button(this);stop.setText("Stop / disarm");stop.setOnClickListener(v->{
            getSharedPreferences("probe",0).edit().putBoolean("armed",false).apply();
            startService(new Intent(this,DashboardService.class).setAction("com.kalyan.bmwdashboardprobe.STOP"));update();
        });actions.addView(stop);root.addView(actions);
        root.addView(new Preview(this),new LinearLayout.LayoutParams(-1,0,1));setContentView(root);update();
        consumeArmIntent();
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);setIntent(intent);
        Log.i(DashboardService.TAG,"Activity warm intent build="+BuildIdentity.VERSION);consumeArmIntent();
    }
    private void consumeArmIntent() {
        boolean requested=getIntent().getBooleanExtra("arm",false);
        getIntent().removeExtra("arm");
        if(requested){Log.i(DashboardService.TAG,"Arm extra consumed build="+BuildIdentity.VERSION);arm();}
    }
    private void arm() {
        getSharedPreferences("probe",0).edit().putBoolean("armed",true).apply();
        // If already bound, use the saved local tunnel; otherwise wait for AAIdrive's next connection.
        startService(new Intent(this,DashboardService.class));
        sendBroadcast(new Intent("me.hufman.androidautoidrive.CarConnectionListener_START").setComponent(
            new ComponentName(DashboardService.HOST_PACKAGE,"me.hufman.androidautoidrive.CarConnectionListener")));
        update();
    }
    private void update() {status.setText("Dashboard Probe "+BuildIdentity.VERSION+" · "+BuildIdentity.SOURCE_SHA256.substring(0,12)+"\n"+(getSharedPreferences("probe",0).getBoolean("armed",false)?"Armed once — awaiting car connection":"Local preview — not armed"));}
    private static final class Preview extends View {
        final DashboardRenderer renderer=new DashboardRenderer();final ProbeState state=new ProbeState();long frame;
        Preview(Context c){super(c);setFocusable(true);setFocusableInTouchMode(true);}
        @Override protected void onDraw(Canvas c){renderer.draw(c,getWidth(),getHeight(),state,frame++,0,0);if(state.fpsLimit>0)postInvalidateDelayed(1000/state.fpsLimit);}
        @Override public boolean onTouchEvent(MotionEvent e){if(e.getAction()==MotionEvent.ACTION_UP){state.rotate(1,SystemClock.elapsedRealtimeNanos());invalidate();}return true;}
        @Override public boolean onKeyDown(int key,KeyEvent e){
            if(key==KeyEvent.KEYCODE_DPAD_LEFT||key==KeyEvent.KEYCODE_DPAD_RIGHT)state.rotate(key==KeyEvent.KEYCODE_DPAD_LEFT?-1:1,SystemClock.elapsedRealtimeNanos());
            else if(key==KeyEvent.KEYCODE_DPAD_CENTER||key==KeyEvent.KEYCODE_ENTER)state.click(SystemClock.elapsedRealtimeNanos());else return super.onKeyDown(key,e);
            invalidate();return true;
        }
    }
}
