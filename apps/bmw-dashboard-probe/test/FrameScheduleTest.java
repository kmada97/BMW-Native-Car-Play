import com.kalyan.bmwdashboardprobe.FrameSchedule;
import com.kalyan.bmwdashboardprobe.DashboardLayout;
import com.kalyan.bmwdashboardprobe.ProbeState;

public final class FrameScheduleTest {
    static void require(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
    static void send(FrameSchedule f,long at) {f.sent(at,f.revision(),f.quality(at));}
    public static void main(String[] args) {
        FrameSchedule f=new FrameSchedule();
        require(f.delay(0,0,false)==0,"Initial image required");send(f,0);
        require(f.delay(10000,0,false)==FrameSchedule.NEVER,"Static dashboard produces no periodic image traffic");
        f.input(10001);
        require(f.delay(10001,2,false)==0,"Input bypasses low animation rate");
        require(f.quality(10001)==40,"USB interaction uses upstream quality40");
        require(f.delay(10001,0,true)>0,"Queued input runs before image RPC");
        long previous=f.revision();f.input(10002);f.input(10003);
        require(f.revision()==previous+2,"Every knob callback retained in newest state");
        send(f,10003);
        require(f.delay(10004,0,false)==4999,"Burst coalesces into one frame then one settle timer");
        require(f.quality(15002)==40&&f.quality(15003)==65,"Interaction quality window extends with newest input");
        require(f.delay(15003,0,false)==0,"One high-quality settled frame");send(f,15003);
        require(f.delay(15004,0,false)==FrameSchedule.NEVER,"Settled frame does not create an endless redraw loop");
        f.invalidate();long older=f.revision();f.input(16000);f.sent(16000,older,40);
        require(f.delay(16001,0,false)==0,"Changes newer than captured frame cannot be dropped");send(f,16001);
        require(f.delay(16002,2,false)==499,"Animation obeys configured ceiling");
        require(f.delay(16501,2,false)==0,"Animation frame ready after interval");
        require(f.delay(16900,2,true)>0,"Slow image RPC cannot start another image ahead of queued input");
        send(f,16900);
        require(f.delay(16901,2,false)==499,"No backlog or catch-up animation burst");
        require(f.delay(16901,0,false)>499,"Turning animation off cancels periodic animation work");
        require(ProbeState.SESSION_MS==900000,"Session bounds to15minutes");
        int[][] sizes={{731,480},{1120,480},{640,360},{200,200},{2048,1024}};
        for(int[] size:sizes) {
            DashboardLayout l=new DashboardLayout(size[0],size[1]);
            require(Math.abs(l.width*l.scale-size[0])<0.01,"Canvas horizontal bounds");
            require(Math.abs(l.height*l.scale-size[1])<0.01,"Canvas vertical bounds");
            require(l.contentHeight>0&&l.sideWidth>0&&l.tileWidth>0,"Positive responsive panels");
            require(l.sideX+l.sideWidth<=l.width-l.pad+0.01,"Sidebar within reported canvas");
            require(l.bottom+l.navHeight<l.height-30,"Controls leave room for metrics");
            require(l.pad+4*l.tileWidth+3*l.gap<=l.width-l.pad+0.01,"All4tiles fit");
        }
        System.out.println("PASS: idle suppression, input priority/coalescing, adaptive quality/refinement, animation pacing, session bound, responsive geometry");
    }
}
