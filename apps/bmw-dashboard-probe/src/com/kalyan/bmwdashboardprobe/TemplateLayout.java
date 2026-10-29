package com.kalyan.bmwdashboardprobe;

import java.io.ByteArrayInputStream;
import java.util.ArrayList;
import java.util.List;
import java.nio.charset.StandardCharsets;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

/** Finds the same plain image/list state as AAIdrive FullImageView, without editing signed XML. */
public final class TemplateLayout {
    public int state, titleModel, image, imageModel, input, inputModel, clickAction, selectAction, focusEvent;
    public final List<Integer> components = new ArrayList<>();
    public final List<Integer> entryTargetModels = new ArrayList<>();
    public final List<Integer> entryTextModels = new ArrayList<>();
    public final List<Integer> entryRaActions = new ArrayList<>();

    static int attr(Element e, String name) { return Integer.parseInt(e.getAttribute(name)); }
    static Element first(Element e, String tag) {
        return (Element)e.getElementsByTagName(tag).item(0);
    }
    static Element byId(Document d, int id) {
        NodeList all = d.getElementsByTagName("*");
        for (int i=0; i<all.getLength(); i++) {
            Element e=(Element)all.item(i);
            if (Integer.toString(id).equals(e.getAttribute("id"))) return e;
        }
        throw new IllegalArgumentException("Unknown RHMI id " + id);
    }
    public static TemplateLayout parse(byte[] xml) throws Exception {
        DocumentBuilderFactory factory=DocumentBuilderFactory.newInstance();
        // Android's bundled XML parser does not support every desktop JAXP feature.
        // Only an installed, signed template is accepted; reject declarations before parsing.
        String source=new String(xml,StandardCharsets.UTF_8);
        if(source.contains("<!DOCTYPE")||source.contains("<!ENTITY"))throw new IllegalArgumentException("XML declarations not accepted");
        Document d=factory.newDocumentBuilder().parse(new ByteArrayInputStream(xml));
        TemplateLayout out=new TemplateLayout();
        NodeList states=d.getElementsByTagName("hmiState");
        for (int i=0;i<states.getLength();i++) {
            Element s=(Element)states.item(i), image=first(s,"image"), list=first(s,"list");
            if (image==null || list==null) continue;
            out.state=attr(s,"id"); out.titleModel=attr(s,"textModel");
            out.image=attr(image,"id"); out.imageModel=attr(image,"model");
            out.input=attr(list,"id"); out.inputModel=attr(list,"model");
            out.clickAction=attr(list,"action"); out.selectAction=attr(list,"selectAction");
            NodeList children=first(s,"components").getChildNodes();
            for (int j=0;j<children.getLength();j++) if(children.item(j) instanceof Element)
                out.components.add(attr((Element)children.item(j),"id"));
            break;
        }
        if(out.state==0) throw new IllegalArgumentException("No image/list state in installed template");
        out.focusEvent=attr((Element)d.getElementsByTagName("focusEvent").item(0),"id");
        NodeList entries=d.getElementsByTagName("entryButton");
        for(int i=0;i<entries.getLength();i++) {
            Element entry=(Element)entries.item(i);
            Element action=byId(d,attr(entry,"action"));
            Element hmi=action.getTagName().equals("hmiAction")?action:first(action,"hmiAction");
            Element ra=action.getTagName().equals("raAction")?action:first(action,"raAction");
            if(hmi!=null && hmi.hasAttribute("targetModel")) out.entryTargetModels.add(attr(hmi,"targetModel"));
            if(ra!=null) out.entryRaActions.add(attr(ra,"id"));
            if(entry.hasAttribute("textModel")) {
                Element model=byId(d,attr(entry,"textModel"));
                if(model.getTagName().equals("raDataModel")) out.entryTextModels.add(attr(entry,"textModel"));
            }
        }
        return out;
    }
}
