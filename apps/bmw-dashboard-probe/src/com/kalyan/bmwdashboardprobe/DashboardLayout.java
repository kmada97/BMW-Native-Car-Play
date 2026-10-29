package com.kalyan.bmwdashboardprobe;

/** Canvas geometry in logical pixels with one uniform scale; never stretches text or shapes. */
public final class DashboardLayout {
    public final float scale,width,height,pad,gap,header,bottom,navHeight,contentHeight,mapWidth,sideX,sideWidth,tileWidth;
    public DashboardLayout(int pixelsWide,int pixelsHigh) {
        if(pixelsWide<=0||pixelsHigh<=0)throw new IllegalArgumentException("Positive dimensions required");
        scale=Math.min(pixelsWide/640f,pixelsHigh/360f);
        width=pixelsWide/scale;height=pixelsHigh/scale;
        pad=16;gap=12;header=48;navHeight=52;bottom=height-88;
        contentHeight=bottom-gap-header;
        mapWidth=(width-2*pad-gap)*0.57f;sideX=pad+mapWidth+gap;sideWidth=width-pad-sideX;
        tileWidth=(width-2*pad-3*gap)/4;
    }
}
