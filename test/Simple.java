import org.cprover.CProver;

public class Simple {

  static int ___val = 0;

    public static void main(String[] args) {
      int secret = CProver.nondetInt(); // get a random integer

      // the actual program
      int val = secret | 1;
      if (val > 32){
        val = 1;
      }
      ___val = val;

      assert(___val > 1);
    }
}
