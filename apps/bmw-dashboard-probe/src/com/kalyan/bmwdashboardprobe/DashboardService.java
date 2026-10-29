package com.kalyan.bmwdashboardprobe;

import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.*;
import android.util.Log;
import de.bmw.idrive.BMWRemoting;
import de.bmw.idrive.BMWRemotingServer;
import de.bmw.idrive.BaseBMWRemotingClient;
import io.bimmergestalt.idriveconnectkit.IDriveConnection;
import io.bimmergestalt.idriveconnectkit.RHMIDimensions;
import io.bimmergestalt.idriveconnectkit.RHMIUtils;
import io.bimmergestalt.idriveconnectkit.android.CertMangling;
import io.bimmergestalt.idriveconnectkit.android.security.SecurityAccess;
import io.bimmergestalt.idriveconnectkit.rhmi.RHMIApplicationEtch;
import io.bimmergestalt.idriveconnectkit.rhmi.RHMIModel;
import io.bimmergestalt.idriveconnectkit.rhmi.deserialization.RHMIApplicationKt;
import java.io.*;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.atomic.AtomicInteger;
import org.json.JSONObject;

/** An ordinary AAIdrive connection add-on. All network writes stay on one bounded worker queue. */
public final class DashboardService extends Service {
    public static final String TAG="BMWDashboardProbe", HOST_PACKAGE="me.hufman.androidautoidrive";
    private final IBinder binder=new Binder();
    private HandlerThread thread;
    private Handler worker;
    private Intent latestConnection;
    private BMWRemotingServer remote;
    private volatile ProbeGuard guard;
    private final ScheduledExecutorService timers=Executors.newScheduledThreadPool(2);
    private SecurityAccess security;
    private RHMIApplicationEtch app;
    private TemplateLayout layout;
    private RHMIDimensions dimensions;
    private Bitmap bitmap;
    private Canvas canvas;
    private final ByteArrayOutputStream jpeg=new ByteArrayOutputStream();
    private final DashboardRenderer renderer=new DashboardRenderer();
    private ProbeState state=new ProbeState();
    private FrameSchedule frames=new FrameSchedule();
    private volatile AtomicInteger pendingInputs=new AtomicInteger();
    private PrintWriter metrics;
    private int handle=-1, consecutiveErrors;
    private boolean focused, connecting, running;
    private long frame, startNs, lastInputLogged, openRequestedNs;
    private double lastRpcMs, lastInputMs;

    @Override public void onCreate() {
        super.onCreate();
        Log.i(TAG,"Service created build="+BuildIdentity.VERSION+" source="+BuildIdentity.SOURCE_SHA256);
        thread=new HandlerThread(TAG);thread.start();worker=new Handler(thread.getLooper());
    }
    @Override public IBinder onBind(Intent intent) { accept(intent);return binder; }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        if(intent!=null && "com.kalyan.bmwdashboardprobe.STOP".equals(intent.getAction())) {
            getSharedPreferences("probe",0).edit().putBoolean("armed",false).apply();
            cancelNow("stopped");
            worker.post(() -> close("stopped"));
        } else accept(intent);
        return START_NOT_STICKY;
    }
    private void accept(Intent intent) {
        if(intent!=null && intent.hasExtra("EXTRA_HOST")) latestConnection=new Intent(intent);
        Intent connection=latestConnection==null?null:new Intent(latestConnection);
        if(connection!=null) worker.post(() -> {
            if(running || connecting || !getSharedPreferences("probe",0).getBoolean("armed",false)) return;
            // Only a one-shot, explicitly armed test can take focus; a normal reconnect does nothing.
            getSharedPreferences("probe",0).edit().putBoolean("armed",false).apply();
            connecting=true;
            try { connect(connection); }
            catch(Throwable e) { failure("connect",e);close("connect_error"); }
            finally { connecting=false; }
        });
    }
    private static byte[] read(InputStream stream) throws IOException {
        try(InputStream in=stream;ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] buf=new byte[8192];int n;while((n=in.read(buf))!=-1)out.write(buf,0,n);return out.toByteArray();
        }
    }
    private void connect(Intent intent) throws Exception {
        String host=intent.getStringExtra("EXTRA_HOST"),brand=intent.getStringExtra("EXTRA_BRAND");
        int port=intent.getIntExtra("EXTRA_PORT",-1);
        if(!("127.0.0.1".equals(host)||"localhost".equals(host)) || port<1024 || port>65535)
            throw new IllegalArgumentException("Only the local BMW USB tunnel is supported");
        if(brand==null || !(brand.toUpperCase(Locale.US).startsWith("BMW") || brand.toUpperCase(Locale.US).startsWith("MINI")))
            throw new IllegalArgumentException("Unexpected connection brand");
        File logDir=new File(getFilesDir(),"metrics");if(!logDir.exists()&&!logDir.mkdirs())throw new IOException("Metrics directory");
        metrics=new PrintWriter(new FileOutputStream(new File(logDir,"session-"+System.currentTimeMillis()+".jsonl")),true);
        startNs=SystemClock.elapsedRealtimeNanos();frame=0;focused=false;lastInputLogged=0;
        state=new ProbeState();frames=new FrameSchedule();pendingInputs=new AtomicInteger();
        lastRpcMs=0;lastInputMs=0;consecutiveErrors=0;
        // Each watchdog captures its own connection reference. A stale timer cannot close a later session.
        AtomicReference<BMWRemotingServer> ownedTransport=new AtomicReference<>();
        ProbeGuard sessionGuard=new ProbeGuard(timers,ProbeState.SESSION_MS,reason -> {
            Log.w(TAG,"Independent cancellation: "+reason);
            BMWRemotingServer transport=ownedTransport.get();
            if(transport!=null)try{IDriveConnection.INSTANCE.disconnectEtchConnection(transport);}catch(Throwable ignored){}
        });
        guard=sessionGuard;
        record("start","port",port,"duration_limit_seconds",ProbeState.SESSION_MS/1000,
            "version",BuildIdentity.VERSION,"source_sha256",BuildIdentity.SOURCE_SHA256,
            "frame_policy","on_change; USB JPEG40 interaction,65 settled; optional animation");
        // Resource-only context; no code is loaded from AAIdrive, and its install/config is untouched.
        Context assetsContext=createPackageContext(HOST_PACKAGE,Context.CONTEXT_IGNORE_SECURITY);
        byte[] xml=read(assetsContext.getAssets().open("carapplications/smartthings/rhmi/ui_description.xml"));
        byte[] rawCert=read(assetsContext.getAssets().open("carapplications/smartthings/smartthings.p7b"));
        byte[] images=read(assetsContext.getAssets().open("carapplications/smartthings/rhmi/common/images.zip"));
        byte[] texts=read(assetsContext.getAssets().open("carapplications/smartthings/rhmi/common/texts.zip"));
        layout=TemplateLayout.parse(xml);
        security=SecurityAccess.Companion.getInstance(this);security.connect();
        // My BMW's module is synchronous, while older BMW service bindings complete on Android's main thread.
        // This wait is on our worker only and is bounded; never race a pending service callback.
        long securityDeadline=SystemClock.elapsedRealtime()+5000;
        while(!security.isConnected(brand)&&SystemClock.elapsedRealtime()<securityDeadline&&!sessionGuard.isCancelled())Thread.sleep(50);
        if(sessionGuard.isCancelled())throw new InterruptedIOException("Cancelled before tunnel setup");
        if(!security.isConnected(brand))throw new IOException("BMW security module unavailable");
        byte[] certificate=CertMangling.INSTANCE.mergeBMWCert(rawCert,security.fetchBMWCerts("Dashboard Probe",brand));
        BMWRemotingServer transport=IDriveConnection.INSTANCE.getEtchConnection(host,port,new Events());
        ownedTransport.set(transport);
        if(sessionGuard.isCancelled()) {
            timers.execute(()->{try{IDriveConnection.INSTANCE.disconnectEtchConnection(transport);}catch(Throwable ignored){}});
            throw new InterruptedIOException("Cancelled during tunnel setup");
        }
        // Etch's shipped result types have infinite waits and are locked. Keep its classes unchanged;
        // interrupt a stalled RPC by closing only this probe's tunnel from an independent thread.
        remote=(BMWRemotingServer)Proxy.newProxyInstance(BMWRemotingServer.class.getClassLoader(),
            new Class<?>[]{BMWRemotingServer.class},(proxy,method,args)->sessionGuard.call(method.getName(),8000,()->{
                try{return method.invoke(transport,args);}
                catch(InvocationTargetException e){Throwable cause=e.getCause();if(cause instanceof Exception)throw (Exception)cause;throw (Error)cause;}
            }));
        byte[] challenge=remote.sas_certificate(certificate);
        remote.sas_login(security.signChallenge("Dashboard Probe",challenge));
        Map<?,?> caps=remote.rhmi_getCapabilities("",255);
        Map<String,String> screenCaps=new HashMap<>();
        for(Map.Entry<?,?> entry:caps.entrySet()) {
            String key=String.valueOf(entry.getKey());
            if(key.startsWith("hmi.") || key.equals("a4axl"))screenCaps.put(key,String.valueOf(entry.getValue()));
        }
        dimensions=RHMIDimensions.Companion.create(screenCaps);
        int width=dimensions.getVisibleWidth(),height=dimensions.getVisibleHeight();
        if(width<200||height<200||width>2048||height>1024)throw new IOException("Unexpected screen dimensions "+width+"x"+height);
        record("capabilities","screen",new JSONObject(screenCaps),"physical_width",dimensions.getRhmiWidth(),
            "physical_height",dimensions.getRhmiHeight(),"canvas_width",width,"canvas_height",height,
            "left_margin",dimensions.getMarginLeft(),"right_margin",dimensions.getMarginRight(),
            "padding_left",dimensions.getPaddingLeft(),"padding_top",dimensions.getPaddingTop(),
            "dimensions_reported",screenCaps.containsKey("hmi.display-width")&&screenCaps.containsKey("hmi.display-height"),
            "canvas_basis","IDriveConnectKit layout margins, not optical measurement");
        handle=remote.rhmi_create(null,new BMWRemoting.RHMIMetaData("com.kalyan.bmwdashboardprobe",new BMWRemoting.VersionInfo(0,2,0),"Dashboard Probe","Kalyan"));
        RHMIUtils.INSTANCE.rhmi_setResourceCached(remote,handle,BMWRemoting.RHMIResourceType.DESCRIPTION,xml);
        RHMIUtils.INSTANCE.rhmi_setResourceCached(remote,handle,BMWRemoting.RHMIResourceType.IMAGEDB,images);
        // The template entry uses textId 162 (SmartThings), not a mutable text model.
        // Preserve that signed template and load its text database for a valid manual-reentry label.
        RHMIUtils.INSTANCE.rhmi_setResourceCached(remote,handle,BMWRemoting.RHMIResourceType.TEXTDB,texts);
        remote.rhmi_initialize(handle);
        app=new RHMIApplicationEtch(remote,handle);RHMIApplicationKt.loadFromXML(app,xml);
        app.getModels().get(layout.titleModel).asRaDataModel().setValue("Dashboard Probe");
        for(int model:layout.entryTargetModels) app.getModels().get(model).asRaIntModel().setValue(layout.state);
        for(int model:layout.entryTextModels) app.getModels().get(model).asRaDataModel().setValue("Dashboard Probe");
        property(layout.state,24,3);property(layout.state,26,"1,0,7");
        for(int component:layout.components) property(component,3,false);
        property(layout.image,3,true);property(layout.image,20,-dimensions.getPaddingLeft());
        property(layout.image,21,-dimensions.getPaddingTop());property(layout.image,9,width);property(layout.image,10,height);
        RHMIModel.RaListModel.RHMIListConcrete rows=new RHMIModel.RaListModel.RHMIListConcrete(3,0,0);
        for(int i=0;i<7;i++) rows.addRow(new Object[]{i<3?"+":i>3?"-":"Dashboard Probe","",""});
        app.getModels().get(layout.inputModel).asRaListModel().setValue(rows);
        property(layout.input,3,true);property(layout.input,20,-50000);property(layout.input,21,0);
        property(layout.input,22,true);
        remote.rhmi_addActionEventHandler(handle,"dashboard-probe",-1);
        remote.rhmi_addHmiEventHandler(handle,"dashboard-probe",-1,-1);
        bitmap=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888);canvas=new Canvas(bitmap);
        running=true;
        sendFrame();
        // One normal app focus request. Never repeatedly seize focus after Back, MENU or another app.
        openRequestedNs=SystemClock.elapsedRealtimeNanos();focus(layout.state,null);
        record("focus_requested","state",layout.state);
        worker.postDelayed(() -> {if(running)close("fifteen_minute_limit");},Math.max(1,ProbeState.SESSION_MS-(SystemClock.elapsedRealtimeNanos()-startNs)/1000000));
        worker.postDelayed(() -> {if(running&&!focused)record("focus_unconfirmed_after_5s");},5000);
    }
    private void property(int component,int property,Object value) throws Exception {
        remote.rhmi_setProperty(handle,component,property,Collections.singletonMap(0,value));
    }
    private void focus(int target,Integer row) throws Exception {
        Map<Integer,Object> args=new HashMap<>();args.put(0,target);if(row!=null)args.put(41,row);
        remote.rhmi_triggerEvent(handle,layout.focusEvent,args);
    }
    private final Runnable tick=new Runnable() {
        @Override public void run() {
            if(!running||!focused)return;
            long delay=frames.delay(SystemClock.elapsedRealtime(),state.fpsLimit,pendingInputs.get()>0);
            if(delay!=0){scheduleFrame(delay);return;}
            try {sendFrame();consecutiveErrors=0;}
            catch(Throwable e) {failure("frame",e);if(++consecutiveErrors>=3){close("frame_errors");return;}}
            scheduleFrame(frames.delay(SystemClock.elapsedRealtime(),state.fpsLimit,pendingInputs.get()>0));
        }
    };
    private void scheduleFrame(long delayMs) {
        worker.removeCallbacks(tick);
        if(running&&focused&&delayMs!=FrameSchedule.NEVER)worker.postDelayed(tick,Math.max(1,delayMs));
    }
    private void sendFrame() throws Exception {
        long before=SystemClock.elapsedRealtimeNanos(),revision=frames.revision();
        int quality=frames.quality(before/1000000);
        renderer.draw(canvas,bitmap.getWidth(),bitmap.getHeight(),state,frame,lastRpcMs,lastInputMs);
        long rendered=SystemClock.elapsedRealtimeNanos();
        jpeg.reset();if(!bitmap.compress(Bitmap.CompressFormat.JPEG,quality,jpeg))throw new IOException("JPEG encoding failed");
        byte[] bytes=jpeg.toByteArray();long encoded=SystemClock.elapsedRealtimeNanos();
        app.getModels().get(layout.imageModel).asRaImageModel().setValue(bytes);
        long done=SystemClock.elapsedRealtimeNanos();lastRpcMs=(done-encoded)/1e6;
        frames.sent(before/1000000,revision,quality);
        record("frame","frame",frame++,"bytes",bytes.length,"jpeg_quality",quality,"revision",revision,
            "render_ms",(rendered-before)/1e6,"encode_ms",(encoded-rendered)/1e6,"rpc_ms",lastRpcMs,
            "complete_ns",done,"animation_limit_fps",state.fpsLimit,"inputs_in_frame",state.inputs,"focused",focused);
        if(state.inputReceivedNs>lastInputLogged) {
            lastInputLogged=state.inputReceivedNs;lastInputMs=(done-state.inputReceivedNs)/1e6;
            record("input_frame_complete","input",state.inputs,"callback_to_rpc_complete_ms",lastInputMs);
        }
    }
    private static Object arg(Map<?,?> args,int key) {
        if(args==null)return null;
        Object value=args.get((byte)key);return value==null?args.get(key):value;
    }
    private final class Events extends BaseBMWRemotingClient {
        @Override public void rhmi_onActionEvent(Integer incomingHandle,String ident,Integer action,Map<?,?> args) {
            final long received=SystemClock.elapsedRealtimeNanos();
            final Object row=arg(args,1),invoked=arg(args,43);
            final AtomicInteger pending=pendingInputs;pending.incrementAndGet();
            worker.post(() -> {
                try {
                if(!running||incomingHandle==null||incomingHandle!=handle)return;
                final long processed=SystemClock.elapsedRealtimeNanos();
                boolean success=false,changed=false;
                try {
                    if(action==layout.selectAction && row instanceof Number) {
                        int index=((Number)row).intValue();
                        if(index!=3) {state.rotate(index<3?-1:1,received);frames.input(SystemClock.elapsedRealtime());changed=true;focus(layout.input,3);}
                        record("input_rotate","row",index,"selected",state.selected,"callback_ns",received,
                            "callback_queue_ms",(processed-received)/1e6);
                    } else if(action==layout.clickAction) {
                        // A stored favorite opening must not count as a press on a dashboard tile.
                        if(!(invoked instanceof Number&&((Number)invoked).intValue()==2)){state.click(received);frames.input(SystemClock.elapsedRealtime());changed=true;}
                        record("input_click","selected",state.selected,"callback_ns",received,
                            "callback_queue_ms",(processed-received)/1e6);
                    } else if(layout.entryRaActions.contains(action)) {
                        record("entry_open","callback_ns",received);
                    }
                    success=true;
                    if(changed&&focused)scheduleFrame(0);
                } catch(Throwable e){failure("input",e);}
                finally {
                    // A failed recenter must not leave a synchronous native action pending.
                    try {remote.rhmi_ackActionEvent(handle,action,1,success);}
                    catch(Throwable e){failure("input_ack",e);}
                }
                } finally {pending.decrementAndGet();}
            });
        }
        @Override public void rhmi_onHmiEvent(Integer incomingHandle,String ident,Integer component,Integer event,Map<?,?> args) {
            final long received=SystemClock.elapsedRealtimeNanos();final boolean gained=Boolean.TRUE.equals(arg(args,4));
            if(event==null||event!=1||component==null)return;
            worker.post(() -> {
                if(!running||incomingHandle==null||incomingHandle!=handle||component!=layout.state)return;
                focused=gained;worker.removeCallbacks(tick);
                record("focus","gained",gained,"callback_ns",received,"request_to_callback_ms",(received-openRequestedNs)/1e6);
                if(gained)try {focus(layout.input,3);frames.invalidate();scheduleFrame(0);}catch(Throwable e){failure("focus_input",e);}
            });
        }
    }
    private void record(String event,Object... values) {
        try {
            JSONObject json=new JSONObject();json.put("event",event);json.put("elapsed_ms",(SystemClock.elapsedRealtimeNanos()-startNs)/1e6);
            for(int i=0;i<values.length;i+=2)json.put((String)values[i],values[i+1]);
            if(metrics!=null)metrics.println(json.toString());
            if(!event.equals("frame"))Log.i(TAG,json.toString());
        }catch(Exception e){Log.e(TAG,"Metrics failure",e);}
    }
    private void failure(String stage,Throwable e) {
        record("error","stage",stage,"type",e.getClass().getName(),"message",String.valueOf(e.getMessage()));
        Log.e(TAG,"Probe error at "+stage,e);
    }
    private void close(String reason) {
        running=false;focused=false;worker.removeCallbacksAndMessages(null);
        cancelNow(reason);
        record("end","reason",reason,"frames",frame,"inputs",state.inputs);
        // Transport close releases this RHMI session. Never run another synchronous dispose RPC here.
        try {if(security!=null)security.disconnect();}catch(Throwable ignored){}
        if(bitmap!=null){bitmap.recycle();bitmap=null;}
        if(metrics!=null){metrics.close();metrics=null;}
        remote=null;security=null;app=null;handle=-1;
    }
    private void cancelNow(String reason) {ProbeGuard current=guard;if(current!=null)current.cancel(reason);}
    @Override public boolean onUnbind(Intent intent) {
        // This is also a started service, so it may survive a BMW→Mac cable move.
        // Discard the detached tunnel before a warm arm can consume its one-shot request on that stale port.
        latestConnection=null;
        cancelNow("host_unbound");worker.post(()->close("host_unbound"));return true;
    }
    @Override public void onRebind(Intent intent) {accept(intent);}
    @Override public void onDestroy() {cancelNow("service_destroyed");worker.post(()->{close("service_destroyed");thread.quitSafely();timers.shutdown();});super.onDestroy();}
}
