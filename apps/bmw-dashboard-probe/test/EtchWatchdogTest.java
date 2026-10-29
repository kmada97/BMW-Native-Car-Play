import com.kalyan.bmwdashboardprobe.ProbeGuard;
import de.bmw.idrive.*;
import io.bimmergestalt.idriveconnectkit.IDriveConnection;
import java.net.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/** Real loopback Etch transport, deliberately silent peer. No Android, Pi or car access. */
public final class EtchWatchdogTest {
    public static void main(String[] args) throws Exception {
        ScheduledExecutorService timers=Executors.newScheduledThreadPool(2);
        CountDownLatch finish=new CountDownLatch(1);
        AtomicReference<String> reason=new AtomicReference<>();
        try(ServerSocket listener=new ServerSocket(0,1,InetAddress.getLoopbackAddress())) {
            Thread peer=new Thread(()->{
                try(Socket socket=listener.accept()){finish.await(10,TimeUnit.SECONDS);}
                catch(Exception ignored){}
            });peer.setDaemon(true);peer.start();
            BMWRemotingServer transport=IDriveConnection.INSTANCE.getEtchConnection("127.0.0.1",listener.getLocalPort(),new BaseBMWRemotingClient());
            ProbeGuard guard=new ProbeGuard(timers,5000,why->{reason.set(why);IDriveConnection.INSTANCE.disconnectEtchConnection(transport);});
            long before=System.nanoTime();boolean failed=false;
            try {guard.call("sas_certificate",200,()->transport.sas_certificate(new byte[16]));}
            catch(Exception expected){failed=true;}
            long millis=(System.nanoTime()-before)/1000000;
            if(!failed||!"rpc_timeout:sas_certificate".equals(reason.get())||millis>2500)
                throw new AssertionError("Silent-peer RPC did not unblock in bound: "+millis+" ms, "+reason.get());
            guard.cancel("second_cancel");
            if(!"rpc_timeout:sas_certificate".equals(reason.get()))throw new AssertionError("Cancellation must be idempotent");
            boolean followupBlocked=false;
            try{guard.call("must_not_execute",200,()->{throw new AssertionError("Follow-up RPC executed after cancellation");});}
            catch(java.io.InterruptedIOException expected){followupBlocked=true;}
            if(!followupBlocked)throw new AssertionError("Follow-up must be rejected");
            System.out.println("PASS: actual Etch silent-peer RPC interrupted by independent watchdog in "+millis+" ms");
            System.out.println("PASS: cancellation is idempotent and rejects later RPCs");
            // Explicit Stop returns promptly without waiting for the transport callback.
            CountDownLatch blockedClose=new CountDownLatch(1),closeStarted=new CountDownLatch(1);
            ProbeGuard stopGuard=new ProbeGuard(timers,5000,why->{closeStarted.countDown();try{blockedClose.await();}catch(InterruptedException ignored){}});
            before=System.nanoTime();stopGuard.cancel("stop");
            if((System.nanoTime()-before)/1000000>100||!stopGuard.isCancelled())throw new AssertionError("Stop must signal without blocking");
            if(!closeStarted.await(1,TimeUnit.SECONDS))throw new AssertionError("Independent close did not start");
            blockedClose.countDown();
            System.out.println("PASS: Stop signals immediately while close runs independently");
        } finally {finish.countDown();timers.shutdownNow();}
    }
}
