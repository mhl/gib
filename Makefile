OCAMLOPT=ocamlopt
OCAMLOPTFLAGS=-inline 10

.PHONY : clean

%.cmx: %.ml
	ocamlopt $(OCAMLOPTFLAGS) -c $<

all: ometastore find-git-files find-git-repos

ometastore_stub.o: ometastore_stub.c
	$(OCAMLOPT) $(OCAMLOPTFLAGS) -c $<

ometastore: util.cmx folddir.cmx ometastore_stub.o ometastore.cmx
	$(OCAMLOPT) -o $@ unix.cmxa $^

find-git-files: util.cmx folddir.cmx ometastore_stub.o find-git-files.cmx
	$(OCAMLOPT) -o $@ unix.cmxa $^

find-git-repos: util.cmx folddir.cmx ometastore_stub.o find-git-repos.cmx
	$(OCAMLOPT) -o $@ unix.cmxa $^

clean :
	rm -fv *.omc *.cm[aiox] *.cmxa *.opt *.run *.annot