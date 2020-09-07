int nondet(void);



int main(){
  int S = nondet();
  return S & 1; // leaks exactly one bit
}

