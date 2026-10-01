import java.net.*; import java.io.*;
public class TlsProbe {
  public static void main(String[] a) throws Exception {
    String[] urls = {"https://services.gradle.org/distributions/", "https://maven.aliyun.com/repository/public/", "https://dl.google.com/android/repository/repository2-3.xml"};
    for (String u : urls) {
      try { HttpURLConnection c = (HttpURLConnection) new URL(u).openConnection(); c.setConnectTimeout(15000); c.setReadTimeout(15000); c.setRequestMethod("HEAD");
        System.out.println("OK   " + c.getResponseCode() + "  " + u); }
      catch (Exception e) { System.out.println("FAIL " + u + " -> " + e); }
    }
    System.out.println("java.version=" + System.getProperty("java.version"));
  }
}
