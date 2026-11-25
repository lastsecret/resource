package demo;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
@SpringBootApplication
@RestController
public class ProbeApplication {
  public static void main(String[] args) { SpringApplication.run(ProbeApplication.class,args); }
  @GetMapping("/probe/echo") public Map<String,String> echo(@RequestParam(name="q") String q) { return Map.of("q",q); }
  @PostMapping("/probe/body") public Map<String,Integer> body(@RequestBody String body) { return Map.of("length",body.length()); }
  @GetMapping("/probe/health") public Map<String,String> health() { return Map.of("status","UP"); }
}
