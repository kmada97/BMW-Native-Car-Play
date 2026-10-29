import com.kalyan.bmwstartup.RetryPolicy;

public class RetryPolicyTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        RetryPolicy p = new RetryPolicy();
        for (long t = 0; t < 100_000; t += 1_000)
            check(!p.shouldStart(false, t), "No starts without BMW USB");
        check(p.shouldStart(true, 100_000), "First attachment starts promptly");
        for (long t = 100_001; t < 110_000; t += 500)
            check(!p.shouldStart(true, t), "Repeated callbacks must not create duplicate starts");
        for (int i = 1; i < 5; i++) check(p.shouldStart(true, 100_000 + 10_000 * i), "Bounded retry");
        check(!p.shouldStart(true, 999_999_999), "No ongoing start loop on same attachment");
        p.detached();
        check(p.shouldStart(true, 1_000_000_000), "Fast detach event re-arms next attachment");
        check(!p.shouldStart(false, 1_000_000_001), "Absence clears state");
        check(p.shouldStart(true, 1_000_000_002), "Polled detach also re-arms");
        System.out.println("PASS: absence, duplicate callbacks, 5-attempt bound, cooldown, reconnect");
    }
}
