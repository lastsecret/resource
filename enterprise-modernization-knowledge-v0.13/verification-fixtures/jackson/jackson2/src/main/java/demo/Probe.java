package demo;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.MapperFeature;
public final class Probe {
    public static final class Payload { public int z; public Integer a; }
    static void observe(String label, ObjectMapper mapper) throws Exception {
        for (String input : new String[] {"{\"z\":null,\"a\":null}", "{}", "{\"z\":4,\"a\":2}"}) {
            String result;
            try { Payload p = mapper.readValue(input, Payload.class); result = "OK:" + p.z + ":" + p.a; }
            catch (Exception e) { result = "ERROR:" + e.getClass().getSimpleName(); }
            System.out.println("PROBE " + label + " INPUT=" + input + " RESULT=" + result);
        }
        Payload p = new Payload(); p.z=4; p.a=2;
        System.out.println("PROBE " + label + " ORDER=" + mapper.writeValueAsString(p));
    }
    public static void main(String[] args) throws Exception {
        observe("DEFAULT", JsonMapper.builder().build());
        observe("LEGACY_FLAGS", JsonMapper.builder().disable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES).disable(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY).build());
        observe("STRICT_FLAGS", JsonMapper.builder().enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES).enable(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY).build());
    }
}
