package com.kalyan.bmwdashboardprobe;

import android.graphics.*;
import java.util.Locale;

/** Pixels are rendered on the Pi; geometry adapts to the reported image canvas only. */
public final class DashboardRenderer {
    private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final int ink=Color.rgb(235,241,255), muted=Color.rgb(143,164,188), accent=Color.rgb(72,212,230);
    private void text(Canvas c,String s,float x,float y,float size,float available,int color) {
        p.setColor(color);p.setStyle(Paint.Style.FILL);p.setTextSize(size);p.setTypeface(Typeface.create("sans-serif",Typeface.NORMAL));
        float measured=p.measureText(s);if(measured>available)p.setTextSize(size*available/measured);
        c.drawText(s,x,y,p);
    }
    private void box(Canvas c,float x,float y,float w,float h,int color) {
        p.setColor(color);p.setStyle(Paint.Style.FILL);c.drawRoundRect(x,y,x+w,y+h,12,12,p);
    }
    public void draw(Canvas c,int width,int height,ProbeState s,long frame,double rpcMs,double inputMs) {
        DashboardLayout l=new DashboardLayout(width,height);
        c.drawColor(Color.rgb(8,16,27));c.save();c.scale(l.scale,l.scale);
        text(c,"DRIVE / Dashboard Probe "+BuildIdentity.VERSION,l.pad,30,19,l.width-2*l.pad,ink);
        box(c,l.pad,l.header,l.mapWidth,l.contentHeight,Color.rgb(17,34,47));
        // Schematic roads are explicitly demo content, not a navigation route or real location.
        c.save();c.clipRect(l.pad+4,l.header+4,l.pad+l.mapWidth-4,l.header+l.contentHeight-4);
        p.setColor(Color.rgb(39,62,70));p.setStrokeWidth(10);
        for(float x=l.pad-100;x<l.pad+l.mapWidth+100;x+=64)c.drawLine(x,l.header,x+100,l.header+l.contentHeight,p);
        for(float y=l.header+40;y<l.header+l.contentHeight+40;y+=56)c.drawLine(l.pad,y,l.pad+l.mapWidth,y-20,p);
        p.setColor(accent);p.setStrokeWidth(7);p.setStyle(Paint.Style.STROKE);
        Path route=new Path();float rx=l.pad+l.mapWidth*.42f,ry=l.header+l.contentHeight*.82f;
        route.moveTo(rx,ry);route.lineTo(rx-16,l.header+l.contentHeight*.56f);route.lineTo(l.pad+l.mapWidth*.76f,l.header+l.contentHeight*.53f);route.lineTo(l.pad+l.mapWidth*.82f,l.header+40);c.drawPath(route,p);
        p.setStyle(Paint.Style.FILL);p.setColor(ink);c.drawCircle(rx,ry,7,p);c.restore();
        box(c,l.pad+10,l.header+10,l.mapWidth-20,64,Color.rgb(7,20,30));
        text(c,"Navigation canvas",l.pad+22,l.header+36,22,l.mapWidth-44,ink);
        text(c,"DEMO · no live route",l.pad+22,l.header+59,16,l.mapWidth-44,accent);
        float sideHeight=(l.contentHeight-l.gap)/2;
        panel(c,l.sideX,l.header,l.sideWidth,sideHeight,"MUSIC","Bluetooth audio","Live player not connected");
        panel(c,l.sideX,l.header+sideHeight+l.gap,l.sideWidth,sideHeight,"PHONE","Calls / voice","Not connected · demo only");
        String[] labels={"Navigate","Music","Phone","Display test"};
        for(int i=0;i<4;i++) {
            float x=l.pad+i*(l.tileWidth+l.gap);
            box(c,x,l.bottom,l.tileWidth,l.navHeight,i==s.selected?accent:Color.rgb(28,41,58));
            text(c,labels[i],x+12,l.bottom+32,21,l.tileWidth-24,i==s.selected?Color.rgb(5,28,35):ink);
        }
        String mode=s.fpsLimit==0?"On change":"Animation cap "+s.fpsLimit+" fps";
        text(c,String.format(Locale.US,"%dx%d · %s · inputs %d",width,height,mode,s.inputs),l.pad,l.height-21,12,l.width-2*l.pad,muted);
        text(c,String.format(Locale.US,"Last RPC %.0f ms · input→RPC %.0f ms (not screen latency)",rpcMs,inputMs),l.pad,l.height-6,12,l.width-2*l.pad,muted);
        // Animation is opt-in only; the normal dashboard creates no periodic traffic.
        if(s.fpsLimit>0){p.setColor(accent);float x=l.pad+(frame%100)*(l.width-2*l.pad-8)/99;c.drawRect(x,l.bottom-7,x+8,l.bottom-3,p);}
        if(s.detail) {
            float x=l.pad+14,y=l.header+20,w=l.width-2*x,h=Math.min(190,l.contentHeight-40);
            box(c,x,y,w,h,Color.rgb(7,20,32));
            String title=s.selected==0?"Navigation demo":s.selected==1?"Music integration pending":"Calls / voice not connected";
            text(c,title,x+20,y+40,25,w-40,ink);
            text(c,"Factory display and iDrive input are connected.",x+20,y+78,19,w-40,muted);
            text(c,"Real phone apps are not part of this build.",x+20,y+108,19,w-40,muted);
            text(c,"Press the knob again to close.",x+20,y+h-18,19,w-40,accent);
        }
        c.restore();
    }
    private void panel(Canvas c,float x,float y,float w,float h,String label,String title,String sub) {
        box(c,x,y,w,h,Color.rgb(24,32,52));
        text(c,label,x+14,y+25,13,w-28,muted);
        text(c,title,x+14,y+h*.57f,23,w-28,ink);
        text(c,sub,x+14,y+h-16,15,w-28,muted);
    }
}
