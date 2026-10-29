import com.kalyan.bmwdashboardprobe.ProbeState;
import com.kalyan.bmwdashboardprobe.TemplateLayout;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipFile;

public class ProbeTest {
    static void require(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
    public static void main(String[] args) throws Exception {
        ProbeState state=new ProbeState();state.rotate(-1,100);
        require(state.selected==3,"Counter-clockwise wrap");state.click(101);
        require(state.fpsLimit==2,"Animation opt-in starts at2fps");state.click(102);
        require(state.fpsLimit==5,"Frame limit cycle");state.rotate(1,103);
        require(state.selected==0,"Clockwise wrap");state.click(104);
        require(state.detail&&state.inputs==5&&state.inputReceivedNs==104,"Input marker and detail transition");
        state.selected=3;state.click(105);state.click(106);state.click(107);
        require(state.fpsLimit==0,"Animation cycle returns to on-change mode");
        try(ZipFile apk=new ZipFile(args[0])) {
            byte[] xml=apk.getInputStream(apk.getEntry("assets/carapplications/smartthings/rhmi/ui_description.xml")).readAllBytes();
            TemplateLayout layout=TemplateLayout.parse(xml);
            require(layout.state==19&&layout.image==132&&layout.imageModel==531,"Installed template image state");
            require(layout.input==133&&layout.inputModel==532,"Installed template input list");
            require(layout.clickAction==362&&layout.selectAction==363&&layout.focusEvent==6,"Actual callback/focus identifiers");
            require(!layout.entryTargetModels.isEmpty(),"Entry button target available");
            require(layout.components.size()==6,"All other native widgets can be hidden");
        }
        boolean rejected=false;
        try {TemplateLayout.parse("<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]><x/>".getBytes(StandardCharsets.UTF_8));}
        catch(Exception expected){rejected=true;}
        require(rejected,"Reject external entities");
        System.out.println("PASS: knob state, input timing marker, rate transitions, actual signed-template ids, XML entity rejection");
    }
}
