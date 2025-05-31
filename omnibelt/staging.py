from typing import Mapping, Type, List
from .tricks import Dictionary_Capturer


AbstractScape = Mapping



class AbstractStaged:
	@property
	def is_staged(self):
		raise NotImplementedError


	def stage(self, scape: AbstractScape = None):
		raise NotImplementedError



class AbstractSetup(AbstractStaged):
	def setup(self, *args, **kwargs):
		raise NotImplementedError



class Staged(AbstractStaged):
	_is_staged = False
	@property
	def is_staged(self):
		return self._is_staged


	def stage(self, scape: AbstractScape = None):
		if not self.is_staged:
			self._stage(scape)
			self._is_staged = True
		return self


	def _stage(self, scape: AbstractScape):
		pass



class AutoStaged(Staged, AbstractSetup):
	_auto_setup_helper = Dictionary_Capturer
	def _stage(self, scape: AbstractScape):
		self._auto_setup_helper(self, 'setup', scape, agitator=AutoStaged).run()
		return super()._stage(scape)

	def setup(self):
		pass


def test_staged():
	class A(AutoStaged):
		def setup(self, x, y = 10):
			self.x = x
			self.y = y

	class B(A):
		def setup(self, x, y = 10, z = 100):
			super().setup(x, y*2)
			self.z = x + y

	a = A()
	data = {'x': -1, 'y': 1}
	a.stage(data)
	assert a.x == -1 and a.y == 1

	b = B()
	data = {'x': -1, 'y': 1, 'z': -2}
	b.stage(data)
	assert b.x == -1 and b.y == 2 and b.z == 0



# class StagedGaggle(GaggleBase, Staged):
# 	def _stage(self, plan: AbstractPlan):
# 		for gadget in self._gadgets():
# 			if isinstance(gadget, Staged):
# 				gadget.stage(plan)
# 		return super()._stage(plan)







